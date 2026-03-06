"""
ChainSure — Agent Main Tests
Tests for the agent orchestrator with mocked dependencies.
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from agent.main import ChainSureAgent, STATES


class TestChainSureAgent:
    """Tests for the ChainSureAgent orchestrator."""

    def setup_method(self):
        self.agent = ChainSureAgent()

    def test_greeting(self):
        """Agent should return greeting with menu options."""
        response = self.agent.handle_message("+254700000000", "hi", "test-tenant")
        assert "Welcome to ChainSure" in response
        assert "1️⃣" in response

    def test_menu_command(self):
        """Any greeting keyword should show the menu."""
        for keyword in ["hello", "hey", "start", "menu"]:
            response = self.agent.handle_message("+254700000000", keyword, "test-tenant")
            assert "Welcome to ChainSure" in response

    def test_help_command(self):
        """Help command should return help text."""
        response = self.agent.handle_message("+254700000000", "help", "test-tenant")
        assert "Help" in response

    def test_view_policies_option(self):
        """Selecting option 1 should show available policies."""
        # First go to greeting state
        self.agent.handle_message("+254700000000", "hi", "test-tenant")
        # Then select option 1
        response = self.agent.handle_message("+254700000000", "1", "test-tenant")
        assert "Available Insurance Products" in response

    def test_purchase_option(self):
        """Selecting option 2 should start purchase flow."""
        self.agent.handle_message("+254700000000", "hi", "test-tenant")
        response = self.agent.handle_message("+254700000000", "2", "test-tenant")
        assert "Purchase a Policy" in response
        assert "Crop Insurance" in response

    def test_claim_option(self):
        """Selecting option 3 should start claim flow."""
        self.agent.handle_message("+254700000000", "hi", "test-tenant")
        response = self.agent.handle_message("+254700000000", "3", "test-tenant")
        assert "File a Claim" in response

    def test_status_option(self):
        """Selecting option 4 should start status check flow."""
        self.agent.handle_message("+254700000000", "hi", "test-tenant")
        response = self.agent.handle_message("+254700000000", "4", "test-tenant")
        assert "Claim Status" in response

    def test_state_management(self):
        """Agent should track conversation state per user."""
        phone = "+254700000000"
        self.agent.handle_message(phone, "hi", "test-tenant")
        assert self.agent.get_state(phone) == STATES["GREETING"]

        self.agent.handle_message(phone, "3", "test-tenant")
        assert self.agent.get_state(phone) == STATES["CLAIM"]

    def test_tenant_resolution(self):
        """Agent should default to 'default' tenant for unknown numbers."""
        assert self.agent.resolve_tenant("+254700000000") == "default"

    def test_multiple_users(self):
        """Agent should maintain separate state per user."""
        phone_a = "+254700000001"
        phone_b = "+254700000002"

        self.agent.handle_message(phone_a, "hi", "test-tenant")
        self.agent.handle_message(phone_a, "3", "test-tenant")

        self.agent.handle_message(phone_b, "hi", "test-tenant")

        assert self.agent.get_state(phone_a) == STATES["CLAIM"]
        assert self.agent.get_state(phone_b) == STATES["GREETING"]
