"""
ChainSure SaaS — Policy Routes
Policy listing and stats per tenant.
"""

from flask import Blueprint, request, jsonify
from api.auth import require_api_key

policies_bp = Blueprint("policies", __name__)


@policies_bp.route("/<tenant_id>", methods=["GET"])
@require_api_key
def list_policies(tenant_id):
    """List all policies for a tenant."""
    # In production, this reads from the blockchain via ContractReader
    return jsonify({
        "success": True,
        "data": {
            "tenant_id": tenant_id,
            "policies": [],
            "message": "Connect ContractReader to fetch live data",
        },
    })


@policies_bp.route("/<tenant_id>/<int:policy_id>", methods=["GET"])
@require_api_key
def get_policy(tenant_id, policy_id):
    """Get a specific policy's details."""
    return jsonify({
        "success": True,
        "data": {
            "tenant_id": tenant_id,
            "policy_id": policy_id,
            "message": "Connect ContractReader to fetch live data",
        },
    })
