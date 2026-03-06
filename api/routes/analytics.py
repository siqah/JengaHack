"""
ChainSure SaaS — Analytics Routes
Dashboard analytics for tenants.
"""

from flask import Blueprint, jsonify
from api.auth import require_api_key

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/<tenant_id>", methods=["GET"])
@require_api_key
def get_analytics(tenant_id):
    """Get dashboard analytics for a tenant."""
    # In production, aggregates data from blockchain + local DB
    return jsonify({
        "success": True,
        "data": {
            "tenant_id": tenant_id,
            "total_policies": 0,
            "active_policies": 0,
            "total_claims": 0,
            "approved_claims": 0,
            "rejected_claims": 0,
            "pool_balance_usdc": 0.0,
            "total_premiums_usdc": 0.0,
            "total_payouts_usdc": 0.0,
            "claims_ratio": 0.0,
            "message": "Connect ContractReader for live data",
        },
    })


@analytics_bp.route("/overview", methods=["GET"])
@require_api_key
def get_platform_overview():
    """Get platform-wide analytics (all tenants)."""
    return jsonify({
        "success": True,
        "data": {
            "total_tenants": 0,
            "total_policies_platform": 0,
            "total_claims_platform": 0,
            "total_tvl_usdc": 0.0,
            "message": "Aggregate from all tenant contracts",
        },
    })
