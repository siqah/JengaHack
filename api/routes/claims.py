"""
ChainSure SaaS — Claims Routes
Claim management endpoints.
"""

from flask import Blueprint, request, jsonify
from api.auth import require_api_key

claims_bp = Blueprint("claims", __name__)


@claims_bp.route("/<tenant_id>", methods=["GET"])
@require_api_key
def list_claims(tenant_id):
    """List all claims for a tenant."""
    return jsonify({
        "success": True,
        "data": {
            "tenant_id": tenant_id,
            "claims": [],
            "message": "Connect ContractReader to fetch live data",
        },
    })


@claims_bp.route("/<tenant_id>/<int:claim_id>", methods=["GET"])
@require_api_key
def get_claim(tenant_id, claim_id):
    """Get a specific claim's details."""
    return jsonify({
        "success": True,
        "data": {
            "tenant_id": tenant_id,
            "claim_id": claim_id,
            "message": "Connect ContractReader to fetch live data",
        },
    })


@claims_bp.route("/<tenant_id>/<int:claim_id>/approve", methods=["POST"])
@require_api_key
def approve_claim(tenant_id, claim_id):
    """Approve a claim (triggers on-chain approval)."""
    return jsonify({
        "success": True,
        "data": {
            "tenant_id": tenant_id,
            "claim_id": claim_id,
            "action": "approve",
            "message": "Connect ClaimExecutor to execute on-chain",
        },
    })


@claims_bp.route("/<tenant_id>/<int:claim_id>/reject", methods=["POST"])
@require_api_key
def reject_claim(tenant_id, claim_id):
    """Reject a claim with a reason."""
    data = request.get_json() or {}
    reason = data.get("reason", "Not specified")

    return jsonify({
        "success": True,
        "data": {
            "tenant_id": tenant_id,
            "claim_id": claim_id,
            "action": "reject",
            "reason": reason,
            "message": "Connect ClaimExecutor to execute on-chain",
        },
    })
