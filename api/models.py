"""
ChainSure SaaS — API Models
Pydantic models for request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ──────────────────────────────────────────────
#  Tenant Models
# ──────────────────────────────────────────────

class TenantCreate(BaseModel):
    tenant_id: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-z0-9-]+$")
    name: str = Field(..., min_length=1, max_length=100)
    contact_email: str
    whatsapp_numbers: list[str] = []


class TenantResponse(BaseModel):
    tenant_id: str
    name: str
    contact_email: str
    whatsapp_numbers: list[str]
    contracts: Optional[dict] = None
    created_at: Optional[str] = None
    active: bool = True


# ──────────────────────────────────────────────
#  Policy Models
# ──────────────────────────────────────────────

class PolicyResponse(BaseModel):
    policy_id: int
    tenant_id: str
    holder: str
    coverage_type: str
    premium_amount: float
    coverage_limit: float
    start_date: int
    end_date: int
    status: str


# ──────────────────────────────────────────────
#  Claim Models
# ──────────────────────────────────────────────

class ClaimResponse(BaseModel):
    claim_id: int
    policy_id: int
    claimant: str
    tenant_id: str
    amount: float
    status: str
    filed_at: int
    rejection_reason: Optional[str] = None


# ──────────────────────────────────────────────
#  Analytics Models
# ──────────────────────────────────────────────

class AnalyticsResponse(BaseModel):
    tenant_id: str
    total_policies: int = 0
    active_policies: int = 0
    total_claims: int = 0
    approved_claims: int = 0
    rejected_claims: int = 0
    pool_balance_usdc: float = 0.0
    total_premiums_usdc: float = 0.0
    total_payouts_usdc: float = 0.0
    claims_ratio: float = 0.0


# ──────────────────────────────────────────────
#  API Response Wrapper
# ──────────────────────────────────────────────

class APIResponse(BaseModel):
    success: bool
    data: Optional[dict | list] = None
    error: Optional[str] = None
