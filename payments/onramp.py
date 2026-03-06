"""
ChainSure — Coinbase On-Ramp Service
Converts fiat premium payments to USDC via Coinbase On-Ramp.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()


class OnRampService:
    """Integrates with Coinbase On-Ramp to convert fiat → USDC."""

    BASE_URL = "https://api.commerce.coinbase.com"

    def __init__(self):
        self.api_key = os.getenv("COINBASE_API_KEY")
        self.api_secret = os.getenv("COINBASE_API_SECRET")
        self.headers = {
            "Content-Type": "application/json",
            "X-CC-Api-Key": self.api_key,
            "X-CC-Version": "2018-03-22",
        }

    def create_payment_link(
        self,
        amount_fiat: float,
        currency: str,
        tenant_id: str,
        policy_description: str = "Insurance Premium",
    ) -> dict:
        """
        Create a Coinbase Commerce charge for fiat → USDC conversion.

        Args:
            amount_fiat: Amount in local fiat currency.
            currency: ISO currency code (e.g., "KES", "USD").
            tenant_id: Tenant identifier for tracking.
            policy_description: Human-readable description.

        Returns:
            dict with 'charge_id', 'hosted_url', and 'status'.
        """
        payload = {
            "name": f"ChainSure Premium — {tenant_id}",
            "description": policy_description,
            "pricing_type": "fixed_price",
            "local_price": {
                "amount": str(amount_fiat),
                "currency": currency,
            },
            "metadata": {
                "tenant_id": tenant_id,
                "type": "premium_payment",
            },
        }

        try:
            response = requests.post(
                f"{self.BASE_URL}/charges",
                json=payload,
                headers=self.headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()["data"]

            return {
                "charge_id": data["id"],
                "hosted_url": data["hosted_url"],
                "status": data["timeline"][-1]["status"],
                "expires_at": data["expires_at"],
            }

        except requests.RequestException as e:
            return {"error": str(e), "charge_id": None, "hosted_url": None}

    def check_payment_status(self, charge_id: str) -> dict:
        """
        Poll a Coinbase Commerce charge for its current status.

        Returns:
            dict with 'status' (NEW, PENDING, COMPLETED, EXPIRED, etc.)
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/charges/{charge_id}",
                headers=self.headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()["data"]

            return {
                "charge_id": charge_id,
                "status": data["timeline"][-1]["status"],
                "payments": data.get("payments", []),
            }

        except requests.RequestException as e:
            return {"error": str(e), "status": "UNKNOWN"}

    def get_usdc_balance(self, address: str) -> float:
        """
        Check USDC balance of an address on Base via a public RPC.
        Uses the ERC-20 balanceOf method.
        """
        from web3 import Web3

        rpc_url = os.getenv("BASE_SEPOLIA_RPC", "https://sepolia.base.org")
        w3 = Web3(Web3.HTTPProvider(rpc_url))

        usdc_address = os.getenv(
            "USDC_CONTRACT_ADDRESS",
            "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
        )

        # Minimal ERC-20 ABI for balanceOf
        erc20_abi = [
            {
                "constant": True,
                "inputs": [{"name": "account", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function",
            }
        ]

        contract = w3.eth.contract(
            address=Web3.to_checksum_address(usdc_address), abi=erc20_abi
        )
        raw_balance = contract.functions.balanceOf(
            Web3.to_checksum_address(address)
        ).call()

        # USDC has 6 decimals
        return raw_balance / 1e6
