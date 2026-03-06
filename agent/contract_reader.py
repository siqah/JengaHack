"""
ChainSure — Contract Reader
Reads live policy and claim state from Base blockchain via Web3.
"""

import os
import json
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()


class ContractReader:
    """Reads on-chain state for policies, claims, and liquidity pools."""

    def __init__(self, tenant_contracts: dict | None = None):
        """
        Args:
            tenant_contracts: dict with keys 'policyNFT', 'claimsContract',
                              'liquidityPool' mapping to deployed addresses.
        """
        rpc_url = os.getenv("BASE_SEPOLIA_RPC", "https://sepolia.base.org")
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.tenant_contracts = tenant_contracts or {}

        # Load ABIs from Hardhat artifacts (if available)
        self._abis = {}
        self._contracts = {}

        if tenant_contracts:
            self._init_contracts(tenant_contracts)

    def _init_contracts(self, addresses: dict):
        """Initialize contract instances from addresses and ABIs."""
        artifacts_dir = os.path.join(
            os.path.dirname(__file__), "..", "artifacts", "contracts"
        )

        abi_map = {
            "policyNFT": "PolicyNFT.sol/PolicyNFT.json",
            "claimsContract": "ClaimsContract.sol/ClaimsContract.json",
            "liquidityPool": "LiquidityPool.sol/LiquidityPool.json",
        }

        for name, artifact_path in abi_map.items():
            if name in addresses:
                full_path = os.path.join(artifacts_dir, artifact_path)
                try:
                    with open(full_path) as f:
                        artifact = json.load(f)
                    self._abis[name] = artifact["abi"]
                    self._contracts[name] = self.w3.eth.contract(
                        address=Web3.to_checksum_address(addresses[name]),
                        abi=artifact["abi"],
                    )
                except FileNotFoundError:
                    print(f"Warning: ABI not found at {full_path}")

    # ──────────────────────────────────────────────
    #  Policy Reads
    # ──────────────────────────────────────────────

    def get_policy(self, policy_id: int) -> dict | None:
        """Read a policy's on-chain data by ID."""
        contract = self._contracts.get("policyNFT")
        if not contract:
            return None

        try:
            policy = contract.functions.getPolicy(policy_id).call()
            return {
                "policy_id": policy_id,
                "tenant_id": policy[0],
                "holder": policy[1],
                "coverage_type": policy[2],
                "premium_amount": policy[3],
                "coverage_limit": policy[4],
                "start_date": policy[5],
                "end_date": policy[6],
                "status": ["Active", "Expired", "Claimed", "Cancelled"][policy[7]],
                "metadata_uri": policy[8],
            }
        except Exception as e:
            return {"error": str(e)}

    def get_user_policies(self, address: str) -> list[dict]:
        """List all policies owned by a given address."""
        contract = self._contracts.get("policyNFT")
        if not contract:
            return []

        try:
            balance = contract.functions.balanceOf(
                Web3.to_checksum_address(address)
            ).call()

            policies = []
            for i in range(balance):
                token_id = contract.functions.tokenOfOwnerByIndex(
                    Web3.to_checksum_address(address), i
                ).call()
                policy = self.get_policy(token_id)
                if policy:
                    policies.append(policy)
            return policies

        except Exception as e:
            return [{"error": str(e)}]

    def is_policy_active(self, policy_id: int) -> bool:
        """Check if a policy is currently active."""
        contract = self._contracts.get("policyNFT")
        if not contract:
            return False
        try:
            return contract.functions.isActive(policy_id).call()
        except Exception:
            return False

    # ──────────────────────────────────────────────
    #  Claim Reads
    # ──────────────────────────────────────────────

    def get_claim_status(self, claim_id: int) -> dict | None:
        """Read a claim's current state."""
        contract = self._contracts.get("claimsContract")
        if not contract:
            return None

        try:
            claim = contract.functions.getClaim(claim_id).call()
            statuses = ["Filed", "UnderReview", "Approved", "Rejected", "PaidOut"]
            return {
                "claim_id": claim_id,
                "policy_id": claim[0],
                "claimant": claim[1],
                "tenant_id": claim[2],
                "evidence_hash": claim[3].hex(),
                "amount": claim[4],
                "filed_at": claim[5],
                "status": statuses[claim[6]],
                "rejection_reason": claim[7],
            }
        except Exception as e:
            return {"error": str(e)}

    def get_policy_claims(self, policy_id: int) -> list[int]:
        """Get all claim IDs for a policy."""
        contract = self._contracts.get("claimsContract")
        if not contract:
            return []
        try:
            return contract.functions.getPolicyClaims(policy_id).call()
        except Exception:
            return []

    # ──────────────────────────────────────────────
    #  Pool Reads
    # ──────────────────────────────────────────────

    def get_pool_balance(self, tenant_id: str) -> dict:
        """Get the USDC balance of a tenant's liquidity pool."""
        contract = self._contracts.get("liquidityPool")
        if not contract:
            return {"error": "Contract not initialized"}

        try:
            balance, premiums, payouts = contract.functions.getPoolStats(
                tenant_id
            ).call()
            return {
                "tenant_id": tenant_id,
                "balance_usdc": balance / 1e6,
                "total_premiums_usdc": premiums / 1e6,
                "total_payouts_usdc": payouts / 1e6,
            }
        except Exception as e:
            return {"error": str(e)}
