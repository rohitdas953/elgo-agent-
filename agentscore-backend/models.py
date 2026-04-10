from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class AgentStatsResponse(BaseModel):
    total_agents: int
    total_transactions: int
    total_collateral_usdc: float
    avg_score: int
    weekly_agent_growth: float


class LeaderboardAgent(BaseModel):
    rank: int
    alias: str
    wallet: str
    score: int
    tier: str
    transactions: int
    joined_date: str


class LeaderboardResponse(BaseModel):
    agents: list[LeaderboardAgent]
    total: int
    page: int


class AliasCheckResponse(BaseModel):
    available: bool
    alias: str


class FalconCertResponse(BaseModel):
    verified: bool
    cert_hash: str
    issued_at: str
    asa_url: str


class ScoreComponents(BaseModel):
    payment_success_rate: float
    payment_success_count: int
    payment_fail_count: int
    avg_rating: float
    total_ratings: int
    transaction_count: int
    collateral_staked_usdc: float
    account_age_days: int


class X402Policy(BaseModel):
    session_access: bool
    max_session_value_usdc: float
    collateral_required_usdc: float
    payment_mode: str


class ScoreTimelineItem(BaseModel):
    date: str
    score: int


class AgentDetailsResponse(BaseModel):
    alias: str
    wallet: str
    score: int
    tier: str
    asa_id: int
    falcon_cert: FalconCertResponse
    registered_date: str
    score_components: ScoreComponents
    x402_policy: X402Policy
    payment_history: list[dict[str, Any]]
    ratings_received: list[dict[str, Any]]
    score_timeline: list[ScoreTimelineItem]
    algorand_explorer_url: str


class MCPAgentResponse(BaseModel):
    agent_wallet: str
    alias: str
    agent_score: int
    trust_tier: str
    x402_access_policy: X402Policy
    score_components: ScoreComponents
    falcon_cert: FalconCertResponse
    recommendation: str
    algorand_explorer: str


class TransactionItem(BaseModel):
    agent_alias: str | None
    agent_wallet: str
    service_name: str
    amount_usdc: float
    success: bool
    score_change: int
    timestamp: str
    tx_id: str


class RecentTransactionsResponse(BaseModel):
    transactions: list[TransactionItem]


class RegisterAgentRequest(BaseModel):
    wallet: str = Field(min_length=32, max_length=64)
    alias: str = Field(min_length=3, max_length=32)
    collateral: float = Field(ge=0)

    @field_validator("alias")
    @classmethod
    def alias_alphanumeric(cls, value: str) -> str:
        if not value.isalnum():
            raise ValueError("Alias must be alphanumeric")
        return value


class RegisterAgentResponse(BaseModel):
    status: Literal["registered", "updated"]
    wallet: str
    alias: str
    collateral: float
    register_tx_id: str
    registered_at: str


class RecordPaymentRequest(BaseModel):
    agent_wallet: str
    service_name: str
    amount_usdc: float = Field(gt=0)
    success: bool
    score_change: int
    tx_id: str
    agent_alias: str | None = None
    timestamp: datetime | None = None


class RecordPaymentResponse(BaseModel):
    stored: bool
    tx_id: str
