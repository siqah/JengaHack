"""
ChainSure — WhatsApp Business API Handler
Handles incoming/outgoing WhatsApp messages via Meta Cloud API.
"""

import os
import hmac
import hashlib
import json
import requests
from dotenv import load_dotenv

load_dotenv()


class WhatsAppHandler:
    """Manages WhatsApp Business API communication."""

    GRAPH_API = "https://graph.facebook.com/v18.0"

    def __init__(self):
        self.token = os.getenv("WHATSAPP_TOKEN")
        self.phone_id = os.getenv("WHATSAPP_PHONE_ID")
        self.verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    # ──────────────────────────────────────────────
    #  Sending Messages
    # ──────────────────────────────────────────────

    def send_message(self, phone: str, text: str) -> dict:
        """Send a plain text message to a WhatsApp number."""
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": text},
        }
        return self._post(payload)

    def send_template(
        self, phone: str, template_name: str, params: list[str]
    ) -> dict:
        """Send a pre-approved message template."""
        components = []
        if params:
            components.append({
                "type": "body",
                "parameters": [
                    {"type": "text", "text": p} for p in params
                ],
            })

        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "en"},
                "components": components,
            },
        }
        return self._post(payload)

    def send_interactive(self, phone: str, body_text: str, buttons: list[dict]) -> dict:
        """
        Send an interactive button message.

        Args:
            phone: Recipient phone number.
            body_text: Message body text.
            buttons: List of dicts with 'id' and 'title' keys (max 3).
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body_text},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {"id": btn["id"], "title": btn["title"]},
                        }
                        for btn in buttons[:3]  # WhatsApp max 3 buttons
                    ]
                },
            },
        }
        return self._post(payload)

    # ──────────────────────────────────────────────
    #  Receiving Messages (Webhook)
    # ──────────────────────────────────────────────

    def handle_webhook(self, payload: dict) -> dict | None:
        """
        Parse an incoming webhook payload from Meta.

        Returns:
            dict with 'phone', 'message_type', 'text', 'button_id' (if interactive),
            or None if no message found.
        """
        try:
            entry = payload["entry"][0]
            changes = entry["changes"][0]
            value = changes["value"]

            if "messages" not in value:
                return None  # Status update, not a message

            message = value["messages"][0]
            phone = message["from"]
            msg_type = message["type"]

            result = {
                "phone": phone,
                "message_type": msg_type,
                "text": None,
                "button_id": None,
                "timestamp": message.get("timestamp"),
            }

            if msg_type == "text":
                result["text"] = message["text"]["body"]
            elif msg_type == "interactive":
                interactive = message["interactive"]
                if interactive["type"] == "button_reply":
                    result["button_id"] = interactive["button_reply"]["id"]
                    result["text"] = interactive["button_reply"]["title"]
            elif msg_type == "image":
                result["text"] = "[Image received]"
                result["media_id"] = message["image"]["id"]

            return result

        except (KeyError, IndexError):
            return None

    def verify_webhook(self, mode: str, token: str, challenge: str) -> str | None:
        """
        Handle webhook verification from Meta.
        Returns the challenge string if valid, None otherwise.
        """
        if mode == "subscribe" and token == self.verify_token:
            return challenge
        return None

    def verify_signature(self, payload_body: bytes, signature: str) -> bool:
        """Verify the X-Hub-Signature-256 header for webhook security."""
        expected = hmac.new(
            self.token.encode(), payload_body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature)

    # ──────────────────────────────────────────────
    #  Internal
    # ──────────────────────────────────────────────

    def _post(self, payload: dict) -> dict:
        """Send a POST request to the WhatsApp API."""
        try:
            response = requests.post(
                f"{self.GRAPH_API}/{self.phone_id}/messages",
                json=payload,
                headers=self.headers,
                timeout=30,
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.RequestException as e:
            return {"success": False, "error": str(e)}
