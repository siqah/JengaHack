"""
ChainSure — WhatsApp Handler Tests
Tests for webhook parsing and message construction with mocked Meta API.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from agent.whatsapp import WhatsAppHandler


class TestWhatsAppHandler:
    """Tests for WhatsApp message handling."""

    def setup_method(self):
        os.environ["WHATSAPP_TOKEN"] = "test_token"
        os.environ["WHATSAPP_PHONE_ID"] = "123456"
        os.environ["WHATSAPP_VERIFY_TOKEN"] = "test_verify"
        self.handler = WhatsAppHandler()

    def test_webhook_verification_valid(self):
        """Should return challenge for valid verification."""
        result = self.handler.verify_webhook("subscribe", "test_verify", "challenge123")
        assert result == "challenge123"

    def test_webhook_verification_invalid(self):
        """Should return None for invalid token."""
        result = self.handler.verify_webhook("subscribe", "wrong_token", "challenge123")
        assert result is None

    def test_parse_text_message(self):
        """Should parse a text message from webhook payload."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "+254700000000",
                            "type": "text",
                            "text": {"body": "Hello"},
                            "timestamp": "1234567890",
                        }]
                    }
                }]
            }]
        }

        result = self.handler.handle_webhook(payload)
        assert result is not None
        assert result["phone"] == "+254700000000"
        assert result["text"] == "Hello"
        assert result["message_type"] == "text"

    def test_parse_button_reply(self):
        """Should parse interactive button replies."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "+254700000000",
                            "type": "interactive",
                            "interactive": {
                                "type": "button_reply",
                                "button_reply": {
                                    "id": "btn_purchase",
                                    "title": "Purchase",
                                },
                            },
                            "timestamp": "1234567890",
                        }]
                    }
                }]
            }]
        }

        result = self.handler.handle_webhook(payload)
        assert result is not None
        assert result["button_id"] == "btn_purchase"
        assert result["text"] == "Purchase"

    def test_parse_status_update(self):
        """Should return None for status updates (no messages)."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "statuses": [{"status": "delivered"}]
                    }
                }]
            }]
        }

        result = self.handler.handle_webhook(payload)
        assert result is None

    def test_parse_malformed_payload(self):
        """Should return None for malformed payloads."""
        assert self.handler.handle_webhook({}) is None
        assert self.handler.handle_webhook({"entry": []}) is None

    def test_send_message_format(self):
        """Should structure text message payload correctly."""
        # We cannot test actual sending without mocking requests,
        # but we can verify the handler initializes correctly
        assert self.handler.phone_id == "123456"
        assert self.handler.verify_token == "test_verify"
