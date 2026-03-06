"""
ChainSure — Coinbase Paymaster Service
Sponsors gas fees for users via ERC-4337 Account Abstraction,
enabling a gasless user experience.
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()


class PaymasterService:
    """
    Integrates with Coinbase Paymaster to sponsor UserOperations,
    so end-users never pay gas fees on Base.
    """

    def __init__(self):
        self.paymaster_url = os.getenv(
            "COINBASE_PAYMASTER_URL",
            "https://api.developer.coinbase.com/rpc/v1/base-sepolia",
        )
        self.api_key = os.getenv("COINBASE_API_KEY")
        self.headers = {
            "Content-Type": "application/json",
        }

    def sponsor_transaction(self, user_operation: dict) -> dict:
        """
        Submit a UserOperation to the Coinbase Paymaster for gas sponsorship.

        Args:
            user_operation: ERC-4337 UserOperation dict containing:
                - sender, nonce, initCode, callData, callGasLimit,
                  verificationGasLimit, preVerificationGas, maxFeePerGas,
                  maxPriorityFeePerGas, paymasterAndData, signature

        Returns:
            dict with sponsored paymasterAndData, updated gas limits,
            or error information.
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "pm_sponsorUserOperation",
            "params": [
                user_operation,
                os.getenv("FACTORY_CONTRACT_ADDRESS", ""),
            ],
        }

        try:
            response = requests.post(
                self.paymaster_url,
                json=payload,
                headers=self.headers,
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                return {
                    "sponsored": False,
                    "error": result["error"].get("message", "Unknown error"),
                }

            return {
                "sponsored": True,
                "paymasterAndData": result["result"]["paymasterAndData"],
                "callGasLimit": result["result"].get("callGasLimit"),
                "verificationGasLimit": result["result"].get("verificationGasLimit"),
                "preVerificationGas": result["result"].get("preVerificationGas"),
            }

        except requests.RequestException as e:
            return {"sponsored": False, "error": str(e)}

    def is_eligible(self, address: str) -> bool:
        """
        Check if a user address is eligible for gas sponsorship.
        For the MVP, all users are eligible. In production, this could
        check wallet age, transaction count, or tenant-specific rules.
        """
        # MVP: all users get sponsored gas
        if not address or address == "0x" + "0" * 40:
            return False
        return True

    def build_user_operation(
        self,
        sender: str,
        call_data: str,
        nonce: int = 0,
    ) -> dict:
        """
        Build a minimal UserOperation struct for ERC-4337.

        Args:
            sender: Smart wallet address of the user.
            call_data: Encoded contract call data (hex string).
            nonce: User's nonce.

        Returns:
            A UserOperation dict ready for paymaster sponsorship.
        """
        return {
            "sender": sender,
            "nonce": hex(nonce),
            "initCode": "0x",
            "callData": call_data,
            "callGasLimit": hex(500_000),
            "verificationGasLimit": hex(500_000),
            "preVerificationGas": hex(50_000),
            "maxFeePerGas": hex(1_000_000_000),      # 1 gwei
            "maxPriorityFeePerGas": hex(1_000_000),   # 0.001 gwei
            "paymasterAndData": "0x",
            "signature": "0x",
        }
