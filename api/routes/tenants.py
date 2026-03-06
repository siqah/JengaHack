"""
ChainSure SaaS — Tenant Routes
CRUD endpoints for insurance tenant onboarding.
"""

from flask import Blueprint, request, jsonify
from api.auth import require_api_key

tenants_bp = Blueprint("tenants", __name__)

# In-memory store (replace with database in production)
_tenants: dict[str, dict] = {}


@tenants_bp.route("/", methods=["GET"])
@require_api_key
def list_tenants():
    """List all registered tenants."""
    return jsonify({
        "success": True,
        "data": list(_tenants.values()),
    })


@tenants_bp.route("/", methods=["POST"])
@require_api_key
def create_tenant():
    """Register a new insurance tenant."""
    data = request.get_json()

    required_fields = ["tenant_id", "name", "contact_email"]
    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "error": f"Missing field: {field}"}), 400

    tenant_id = data["tenant_id"]
    if tenant_id in _tenants:
        return jsonify({"success": False, "error": "Tenant already exists"}), 409

    tenant = {
        "tenant_id": tenant_id,
        "name": data["name"],
        "contact_email": data["contact_email"],
        "whatsapp_numbers": data.get("whatsapp_numbers", []),
        "contracts": None,
        "active": True,
    }

    _tenants[tenant_id] = tenant
    return jsonify({"success": True, "data": tenant}), 201


@tenants_bp.route("/<tenant_id>", methods=["GET"])
@require_api_key
def get_tenant(tenant_id):
    """Get a specific tenant's details."""
    tenant = _tenants.get(tenant_id)
    if not tenant:
        return jsonify({"success": False, "error": "Tenant not found"}), 404
    return jsonify({"success": True, "data": tenant})


@tenants_bp.route("/<tenant_id>", methods=["PUT"])
@require_api_key
def update_tenant(tenant_id):
    """Update tenant configuration."""
    tenant = _tenants.get(tenant_id)
    if not tenant:
        return jsonify({"success": False, "error": "Tenant not found"}), 404

    data = request.get_json()
    for key in ["name", "contact_email", "whatsapp_numbers", "active"]:
        if key in data:
            tenant[key] = data[key]

    return jsonify({"success": True, "data": tenant})


@tenants_bp.route("/<tenant_id>", methods=["DELETE"])
@require_api_key
def deactivate_tenant(tenant_id):
    """Deactivate a tenant (soft delete)."""
    tenant = _tenants.get(tenant_id)
    if not tenant:
        return jsonify({"success": False, "error": "Tenant not found"}), 404

    tenant["active"] = False
    return jsonify({"success": True, "data": {"message": f"Tenant {tenant_id} deactivated"}})
