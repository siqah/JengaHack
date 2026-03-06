"""
ChainSure — Agent Orchestrator (main.py)
OpenClaw agent entry point with multi-tenant routing and
conversation state machine.
"""

import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv

from agent.whatsapp import WhatsAppHandler
from agent.contract_reader import ContractReader
from agent.claim_executor import ClaimExecutor
from payments.onramp import OnRampService
from payments.paymaster import PaymasterService

load_dotenv()

# ──────────────────────────────────────────────
#  Flask App
# ──────────────────────────────────────────────

app = Flask(__name__)

# ──────────────────────────────────────────────
#  Services
# ──────────────────────────────────────────────

whatsapp = WhatsAppHandler()
onramp = OnRampService()
paymaster = PaymasterService()

# In-memory conversation state (replace with Redis/DB in production)
conversations: dict[str, dict] = {}

# Tenant config loaded from DB/env in production
# Format: phone_number → tenant_id
TENANT_ROUTING: dict[str, str] = {}

# Tenant contract addresses loaded after deployment
# Format: tenant_id → { policyNFT, claimsContract, liquidityPool }
TENANT_CONTRACTS: dict[str, dict] = {}


# ──────────────────────────────────────────────
#  Conversation States
# ──────────────────────────────────────────────

STATES = {
    "GREETING": "greeting",
    "POLICY_INFO": "policy_info",
    "PURCHASE": "purchase",
    "CLAIM": "claim",
    "STATUS": "status",
}


class ChainSureAgent:
    """Multi-tenant insurance agent orchestrator."""

    def __init__(self):
        self.readers: dict[str, ContractReader] = {}
        self.executors: dict[str, ClaimExecutor] = {}

    def get_reader(self, tenant_id: str) -> ContractReader | None:
        """Get or create a ContractReader for a tenant."""
        if tenant_id not in self.readers:
            contracts = TENANT_CONTRACTS.get(tenant_id)
            if not contracts:
                return None
            self.readers[tenant_id] = ContractReader(contracts)
        return self.readers[tenant_id]

    def get_executor(self, tenant_id: str) -> ClaimExecutor | None:
        """Get or create a ClaimExecutor for a tenant."""
        if tenant_id not in self.executors:
            contracts = TENANT_CONTRACTS.get(tenant_id)
            if not contracts:
                return None
            self.executors[tenant_id] = ClaimExecutor(contracts)
        return self.executors[tenant_id]

    def resolve_tenant(self, phone: str) -> str:
        """Resolve tenant ID from user's phone number."""
        return TENANT_ROUTING.get(phone, "default")

    def get_state(self, phone: str) -> str:
        """Get current conversation state for a user."""
        return conversations.get(phone, {}).get("state", STATES["GREETING"])

    def set_state(self, phone: str, state: str, **kwargs):
        """Update conversation state for a user."""
        if phone not in conversations:
            conversations[phone] = {}
        conversations[phone]["state"] = state
        conversations[phone].update(kwargs)

    def handle_message(self, phone: str, text: str, tenant_id: str) -> str:
        """
        Route an incoming message based on conversation state and intent.
        Returns the response text to send back via WhatsApp.
        """
        state = self.get_state(phone)
        text_lower = text.lower().strip()

        # ── Global commands ──
        if text_lower in ("hi", "hello", "hey", "start", "menu"):
            return self._handle_greeting(phone, tenant_id)

        if text_lower in ("help", "?"):
            return self._handle_help()

        # ── State-based routing ──
        if state == STATES["GREETING"]:
            return self._handle_greeting_input(phone, text_lower, tenant_id)
        elif state == STATES["POLICY_INFO"]:
            return self._handle_policy_info(phone, text_lower, tenant_id)
        elif state == STATES["PURCHASE"]:
            return self._handle_purchase(phone, text_lower, tenant_id)
        elif state == STATES["CLAIM"]:
            return self._handle_claim(phone, text_lower, tenant_id)
        elif state == STATES["STATUS"]:
            return self._handle_status(phone, text_lower, tenant_id)
        else:
            return self._handle_greeting(phone, tenant_id)

    # ──────────────────────────────────────────────
    #  State Handlers
    # ──────────────────────────────────────────────

    def _handle_greeting(self, phone: str, tenant_id: str) -> str:
        self.set_state(phone, STATES["GREETING"])
        return (
            "🛡️ *Welcome to ChainSure!*\n\n"
            "I'm your AI insurance assistant. How can I help?\n\n"
            "1️⃣ View available policies\n"
            "2️⃣ Purchase a policy\n"
            "3️⃣ File a claim\n"
            "4️⃣ Check claim status\n"
            "5️⃣ View my policies\n\n"
            "Reply with a number to get started."
        )

    def _handle_help(self) -> str:
        return (
            "ℹ️ *ChainSure Help*\n\n"
            "• Type *menu* to see all options\n"
            "• Type *1-5* to navigate\n"
            "• Type *claim* to file a claim\n"
            "• Type *status* to check a claim\n"
            "• All policies are secured on Base blockchain\n"
            "• Payments are gasless — no crypto needed!\n"
        )

    def _handle_greeting_input(
        self, phone: str, text: str, tenant_id: str
    ) -> str:
        if text == "1":
            self.set_state(phone, STATES["POLICY_INFO"])
            return self._show_available_policies(tenant_id)
        elif text == "2":
            self.set_state(phone, STATES["PURCHASE"])
            return (
                "💳 *Purchase a Policy*\n\n"
                "Which coverage type are you interested in?\n\n"
                "A) 🌾 Crop Insurance\n"
                "B) ✈️ Travel Insurance\n"
                "C) 📱 Device Protection\n\n"
                "Reply with A, B, or C."
            )
        elif text == "3":
            self.set_state(phone, STATES["CLAIM"])
            return (
                "📋 *File a Claim*\n\n"
                "Please provide your Policy ID number.\n"
                "You can find it in your purchase confirmation."
            )
        elif text == "4":
            self.set_state(phone, STATES["STATUS"])
            return "🔍 *Check Claim Status*\n\nPlease enter your Claim ID:"
        elif text == "5":
            return self._show_user_policies(phone, tenant_id)
        else:
            return self._handle_greeting(phone, tenant_id)

    def _handle_policy_info(
        self, phone: str, text: str, tenant_id: str
    ) -> str:
        self.set_state(phone, STATES["GREETING"])
        return self._show_available_policies(tenant_id)

    def _handle_purchase(
        self, phone: str, text: str, tenant_id: str
    ) -> str:
        coverage_map = {
            "a": ("Crop Insurance", 50, 5000),
            "b": ("Travel Insurance", 25, 2500),
            "c": ("Device Protection", 15, 1500),
        }

        if text in coverage_map:
            name, premium, limit = coverage_map[text]

            # Create on-ramp payment link
            result = onramp.create_payment_link(
                amount_fiat=premium,
                currency="USD",
                tenant_id=tenant_id,
                policy_description=f"{name} — Premium Payment",
            )

            self.set_state(phone, STATES["GREETING"], pending_policy=name)

            if result.get("hosted_url"):
                return (
                    f"✅ *{name}*\n\n"
                    f"• Premium: ${premium} USDC\n"
                    f"• Coverage: up to ${limit} USDC\n"
                    f"• Duration: 12 months\n\n"
                    f"💰 Pay here: {result['hosted_url']}\n\n"
                    "Once payment is confirmed, your policy NFT "
                    "will be minted on Base automatically!"
                )
            else:
                return (
                    f"✅ *{name}* selected!\n\n"
                    f"• Premium: ${premium} USDC\n"
                    f"• Coverage: up to ${limit} USDC\n\n"
                    "⚠️ Payment link generation failed. "
                    "Please try again later or type *menu*."
                )
        else:
            return "Please reply with A, B, or C to select a coverage type."

    def _handle_claim(
        self, phone: str, text: str, tenant_id: str
    ) -> str:
        try:
            policy_id = int(text)
        except ValueError:
            return "Please enter a valid Policy ID number."

        reader = self.get_reader(tenant_id)
        if not reader:
            self.set_state(phone, STATES["GREETING"])
            return "⚠️ System unavailable. Please try again later."

        if not reader.is_policy_active(policy_id):
            self.set_state(phone, STATES["GREETING"])
            return (
                "❌ This policy is not active or does not exist.\n"
                "Type *menu* to return to the main menu."
            )

        # For MVP, auto-generate evidence hash from timestamp
        import hashlib
        import time

        evidence = hashlib.sha256(
            f"{policy_id}:{phone}:{int(time.time())}".encode()
        ).hexdigest()

        executor = self.get_executor(tenant_id)
        if not executor:
            self.set_state(phone, STATES["GREETING"])
            return "⚠️ System unavailable. Please try again later."

        policy = reader.get_policy(policy_id)
        result = executor.file_claim(
            policy_id=policy_id,
            evidence_hash=f"0x{evidence}",
            amount=policy.get("coverage_limit", 0),
        )

        self.set_state(phone, STATES["GREETING"])

        if result.get("claim_id") is not None:
            return (
                f"✅ *Claim Filed Successfully!*\n\n"
                f"• Claim ID: {result['claim_id']}\n"
                f"• Policy ID: {policy_id}\n"
                f"• TX: {result['tx_hash'][:10]}...\n\n"
                "Your claim is now being verified through our "
                "6-check automated process. You'll receive an update soon."
            )
        else:
            return (
                f"❌ Failed to file claim: {result.get('error', 'Unknown')}\n"
                "Type *menu* to return."
            )

    def _handle_status(
        self, phone: str, text: str, tenant_id: str
    ) -> str:
        try:
            claim_id = int(text)
        except ValueError:
            return "Please enter a valid Claim ID number."

        reader = self.get_reader(tenant_id)
        if not reader:
            self.set_state(phone, STATES["GREETING"])
            return "⚠️ System unavailable. Please try again later."

        claim = reader.get_claim_status(claim_id)
        self.set_state(phone, STATES["GREETING"])

        if claim and "error" not in claim:
            status_emoji = {
                "Filed": "📝",
                "UnderReview": "🔍",
                "Approved": "✅",
                "Rejected": "❌",
                "PaidOut": "💰",
            }
            emoji = status_emoji.get(claim["status"], "❓")

            response = (
                f"{emoji} *Claim #{claim_id} Status*\n\n"
                f"• Status: {claim['status']}\n"
                f"• Policy ID: {claim['policy_id']}\n"
                f"• Amount: {claim['amount'] / 1e6:.2f} USDC\n"
            )
            if claim.get("rejection_reason"):
                response += f"• Reason: {claim['rejection_reason']}\n"

            return response
        else:
            return "❌ Claim not found. Please check your Claim ID."

    # ──────────────────────────────────────────────
    #  Helpers
    # ──────────────────────────────────────────────

    def _show_available_policies(self, tenant_id: str) -> str:
        return (
            "📋 *Available Insurance Products*\n\n"
            "🌾 *Crop Insurance*\n"
            "  Premium: $50/year | Coverage: up to $5,000\n"
            "  Triggered by verified weather events\n\n"
            "✈️ *Travel Insurance*\n"
            "  Premium: $25/trip | Coverage: up to $2,500\n"
            "  Flight delays, cancellations, lost luggage\n\n"
            "📱 *Device Protection*\n"
            "  Premium: $15/month | Coverage: up to $1,500\n"
            "  Theft, damage, malfunction\n\n"
            "Type *2* to purchase or *menu* for main menu."
        )

    def _show_user_policies(self, phone: str, tenant_id: str) -> str:
        # In production, map phone → wallet address via a user DB
        return (
            "📄 *Your Policies*\n\n"
            "To view your policies, please provide your wallet address "
            "or the email used during purchase."
        )


# ──────────────────────────────────────────────
#  Singleton Agent
# ──────────────────────────────────────────────

agent = ChainSureAgent()


# ──────────────────────────────────────────────
#  Routes
# ──────────────────────────────────────────────


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    """Meta webhook verification endpoint."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    result = whatsapp.verify_webhook(mode, token, challenge)
    if result:
        return result, 200
    return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def handle_webhook():
    """Process incoming WhatsApp messages."""
    payload = request.get_json()
    message = whatsapp.handle_webhook(payload)

    if message and message.get("text"):
        phone = message["phone"]
        text = message["text"]
        tenant_id = agent.resolve_tenant(phone)

        # Generate response
        response_text = agent.handle_message(phone, text, tenant_id)

        # Send response via WhatsApp
        whatsapp.send_message(phone, response_text)

    return jsonify({"status": "ok"}), 200


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "ChainSure Agent",
        "tenants": len(TENANT_CONTRACTS),
    }), 200


# ──────────────────────────────────────────────
#  Entry Point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_ENV") == "development")
