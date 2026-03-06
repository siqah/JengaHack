"""
ChainSure — Claim Executor
Builds and broadcasts claim transactions on behalf of users.
Uses the Paymaster for gasless execution.
"""

import os
import json
import time
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()


class ClaimExecutor:
    """Builds and sends claim transactions on Base."""

    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds

    def __init__(self, tenant_contracts: dict | None = None):
        """
        Args:
            tenant_contracts: dict with 'claimsContract' address.
        """
        rpc_url = os.getenv("BASE_SEPOLIA_RPC", "https://sepolia.base.org")
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.private_key = os.getenv("PRIVATE_KEY")
        self.account = (
            self.w3.eth.account.from_key(self.private_key)
            if self.private_key
            else None
        )

        self._contract = None
        if tenant_contracts and "claimsContract" in tenant_contracts:
            self._init_contract(tenant_contracts["claimsContract"])

    def _init_contract(self, address: str):
        """Load ClaimsContract from Hardhat artifacts."""
        artifact_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "artifacts",
            "contracts",
            "ClaimsContract.sol",
            "ClaimsContract.json",
        )
        try:
            with open(artifact_path) as f:
                artifact = json.load(f)
            self._contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(address),
                abi=artifact["abi"],
            )
        except FileNotFoundError:
            print(f"Warning: ClaimsContract ABI not found at {artifact_path}")

    # ──────────────────────────────────────────────
    #  File a Claim
    # ──────────────────────────────────────────────

    def file_claim(
        self,
        policy_id: int,
        evidence_hash: str,
        amount: int,
        user_address: str | None = None,
    ) -> dict:
        """
        Build and send a fileClaim transaction.

        Args:
            policy_id: The NFT policy ID.
            evidence_hash: Hex string (0x...) of the evidence hash.
            amount: Claim amount in USDC (raw, 6 decimals).
            user_address: Optional — if set, builds the tx for this sender.

        Returns:
            dict with 'tx_hash', 'claim_id', or 'error'.
        """
        if not self._contract or not self.account:
            return {"error": "Contract or account not initialized"}

        try:
            # Convert evidence hash to bytes32
            evidence_bytes = bytes.fromhex(
                evidence_hash.replace("0x", "")
            )
            evidence_bytes32 = evidence_bytes.ljust(32, b"\x00")[:32]

            sender = user_address or self.account.address

            tx = self._contract.functions.fileClaim(
                policy_id, evidence_bytes32, amount
            ).build_transaction({
                "from": sender,
                "nonce": self.w3.eth.get_transaction_count(sender),
                "gas": 500_000,
                "maxFeePerGas": self.w3.to_wei("0.1", "gwei"),
                "maxPriorityFeePerGas": self.w3.to_wei("0.01", "gwei"),
            })

            signed = self.w3.eth.account.sign_transaction(
                tx, self.private_key
            )
            tx_hash = self._send_with_retry(signed)

            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            # Parse claim ID from event logs
            claim_id = self._parse_claim_id(receipt)

            return {
                "tx_hash": tx_hash.hex(),
                "claim_id": claim_id,
                "status": "Filed",
                "gas_used": receipt["gasUsed"],
            }

        except Exception as e:
            return {"error": str(e)}

    def check_claim(self, claim_id: int) -> dict | None:
        """Read claim status from chain."""
        if not self._contract:
            return {"error": "Contract not initialized"}

        try:
            claim = self._contract.functions.getClaim(claim_id).call()
            statuses = ["Filed", "UnderReview", "Approved", "Rejected", "PaidOut"]
            return {
                "claim_id": claim_id,
                "policy_id": claim[0],
                "status": statuses[claim[6]],
                "amount": claim[4],
            }
        except Exception as e:
            return {"error": str(e)}

    # ──────────────────────────────────────────────
    #  Helpers
    # ──────────────────────────────────────────────

    def _send_with_retry(self, signed_tx) -> bytes:
        """Send transaction with retry logic."""
        for attempt in range(self.MAX_RETRIES):
            try:
                return self.w3.eth.send_raw_transaction(
                    signed_tx.raw_transaction
                )
            except Exception as e:
                if attempt == self.MAX_RETRIES - 1:
                    raise
                print(f"Tx attempt {attempt + 1} failed: {e}. Retrying...")
                time.sleep(self.RETRY_DELAY)

    def _parse_claim_id(self, receipt: dict) -> int | None:
        """Extract claim ID from ClaimFiled event in transaction receipt."""
        if not self._contract:
            return None

        try:
            logs = self._contract.events.ClaimFiled().process_receipt(receipt)
            if logs:
                return logs[0]["args"]["claimId"]
        except Exception:
            pass
        return None
