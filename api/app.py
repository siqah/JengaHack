"""
ChainSure SaaS — API Application
Flask REST API for the admin dashboard.
"""

import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from api.routes.tenants import tenants_bp
from api.routes.policies import policies_bp
from api.routes.claims import claims_bp
from api.routes.analytics import analytics_bp

load_dotenv()

app = Flask(__name__)
CORS(app)

# Register blueprints
app.register_blueprint(tenants_bp, url_prefix="/api/tenants")
app.register_blueprint(policies_bp, url_prefix="/api/policies")
app.register_blueprint(claims_bp, url_prefix="/api/claims")
app.register_blueprint(analytics_bp, url_prefix="/api/analytics")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"success": True, "data": {"status": "healthy", "service": "ChainSure SaaS API"}}), 200


@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "error": "Endpoint not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"success": False, "error": "Internal server error"}), 500


if __name__ == "__main__":
    port = int(os.getenv("API_PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_ENV") == "development")
