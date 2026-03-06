"""
ChainSure SaaS — API Key Authentication Middleware
"""

import os
import functools
from flask import request, jsonify
from dotenv import load_dotenv

load_dotenv()


def require_api_key(f):
    """Decorator to enforce API key authentication on routes."""

    @functools.wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        expected_key = os.getenv("API_SECRET_KEY")

        if not expected_key:
            return jsonify({"success": False, "error": "API key not configured"}), 500

        if not api_key:
            return jsonify({"success": False, "error": "Missing X-API-Key header"}), 401

        if api_key != expected_key:
            return jsonify({"success": False, "error": "Invalid API key"}), 403

        return f(*args, **kwargs)

    return decorated
