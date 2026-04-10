from __future__ import annotations

import logging
import os
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from database import (
    get_cached_json,
    get_payment_history_for_wallet,
    get_ratings_for_wallet,
    get_recent_transactions,
    get_registration,
    get_registration_by_alias,
    get_score_timeline,
    init_db,
    insert_payment_record,
    invalidate_cache,
    set_cached_json,
    upsert_registration,
)
from models import (
    AgentDetailsResponse,
    AgentStatsResponse,
    AliasCheckResponse,
    LeaderboardAgent,
    LeaderboardResponse,
    MCPAgentResponse,
    RecentTransactionsResponse,
    RecordPaymentRequest,
    RecordPaymentResponse,
    RegisterAgentRequest,
    RegisterAgentResponse,
)
from services.algorand import AlgorandService
from services.falcon_cert import generate_falcon_cert
from services.score import ScoreService

load_dotenv()


# Configure logging for all bot modules
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()

    # Start Telegram bot (webhook mode)
    from telegram_bot.bot import setup_bot, shutdown_bot

    await setup_bot()
    yield
    await shutdown_bot()


app = FastAPI(title="AgentScore Backend API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Telegram bot webhook + REST routes
from telegram_bot.bot import router as telegram_router  # noqa: E402

app.include_router(telegram_router)

algorand_service = AlgorandService()
score_service = ScoreService()


def _alias_valid(alias: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9]{3,32}", alias))


def _leaderboard_cache_key() -> str:
    return "leaderboard:v1"


def _stats_cache_key() -> str:
    return "stats:v1"


def _agent_cache_key(wallet: str) -> str:
    return f"agent:{wallet}"


def _load_leaderboard_raw() -> list[dict[str, Any]]:
    key = _leaderboard_cache_key()
    cached = get_cached_json(key, ttl_seconds=60)
    if cached and isinstance(cached.get("rows"), list):
        return list(cached["rows"])

    rows = algorand_service.get_leaderboard()
    set_cached_json(key, {"rows": rows})
    return rows


def _load_stats_raw() -> dict[str, Any]:
    key = _stats_cache_key()
    cached = get_cached_json(key, ttl_seconds=30)
    if cached:
        return cached

    stats = algorand_service.get_global_stats()
    set_cached_json(key, stats)
    return stats


def build_agent_details(wallet: str) -> AgentDetailsResponse:
    cached = get_cached_json(_agent_cache_key(wallet), ttl_seconds=30)
    if cached:
        return AgentDetailsResponse.model_validate(cached)

    base_agent = algorand_service.get_agent(wallet)
    if not base_agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    registration = get_registration(wallet)
    alias = registration["alias"] if registration else base_agent["alias"]
    collateral = float(registration["collateral"]) if registration else 0.0
    registered_date = (
        str(registration["registered_at"])[:10]
        if registration and registration.get("registered_at")
        else base_agent.get("registered_date") or datetime.now(UTC).date().isoformat()
    )

    components = score_service.compute_components(
        wallet=wallet,
        base_transaction_count=int(base_agent.get("transactions", 0)),
        fallback_collateral=collateral,
        registered_date=registered_date,
    )
    score = score_service.compute_score(
        components, base_score=int(base_agent.get("score", 0))
    )
    tier = score_service.tier_from_score(score)
    score_service.persist_snapshot(wallet, score)

    raw_asa = base_agent.get("asa_id")
    asa_id = int(raw_asa) if raw_asa is not None else algorand_service.get_asa_for_wallet(wallet)
    falcon_cert = generate_falcon_cert(wallet=wallet, score=score, asa_id=asa_id)
    x402_policy = score_service.x402_policy_for_score(
        score, components["collateral_staked_usdc"]
    )

    payment_history = get_payment_history_for_wallet(wallet, limit=20)
    ratings_received = get_ratings_for_wallet(wallet, limit=20)
    timeline = get_score_timeline(wallet, days=30)

    payload = AgentDetailsResponse(
        alias=alias,
        wallet=wallet,
        score=score,
        tier=tier,
        asa_id=asa_id,
        falcon_cert=falcon_cert,
        registered_date=registered_date,
        score_components=components,
        x402_policy=x402_policy,
        payment_history=payment_history,
        ratings_received=ratings_received,
        score_timeline=timeline,
        algorand_explorer_url=algorand_service.explorer_url(wallet),
    )

    set_cached_json(_agent_cache_key(wallet), payload.model_dump(mode="json"))
    return payload


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/agents/stats", response_model=AgentStatsResponse)
def get_agents_stats() -> AgentStatsResponse:
    data = _load_stats_raw()
    return AgentStatsResponse.model_validate(data)


@app.get("/agents/leaderboard", response_model=LeaderboardResponse)
def get_agents_leaderboard(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
) -> LeaderboardResponse:
    rows = _load_leaderboard_raw()
    total = len(rows)
    start = (page - 1) * limit
    end = start + limit
    sliced = rows[start:end]

    agents = [
        LeaderboardAgent(
            rank=start + idx + 1,
            alias=item["alias"],
            wallet=item["wallet"],
            score=int(item["score"]),
            tier=item.get("tier", score_service.tier_from_score(int(item["score"]))),
            transactions=int(item.get("transactions", 0)),
            joined_date=item.get("joined_date", datetime.now(UTC).date().isoformat()),
        )
        for idx, item in enumerate(sliced)
    ]

    return LeaderboardResponse(agents=agents, total=total, page=page)


@app.get("/agents/check/{alias}", response_model=AliasCheckResponse)
def check_alias(alias: str) -> AliasCheckResponse:
    if not _alias_valid(alias):
        return AliasCheckResponse(available=False, alias=alias)

    if get_registration_by_alias(alias):
        return AliasCheckResponse(available=False, alias=alias)

    available = algorand_service.alias_available(alias)
    return AliasCheckResponse(available=available, alias=alias)


@app.get("/agent/{wallet}", response_model=AgentDetailsResponse)
def get_agent(wallet: str) -> AgentDetailsResponse:
    return build_agent_details(wallet)


@app.get("/agent/{wallet}/mcp-response", response_model=MCPAgentResponse)
def get_agent_mcp_response(wallet: str) -> MCPAgentResponse:
    details = build_agent_details(wallet)
    recommendation = score_service.recommendation_for_tier(details.tier)
    return MCPAgentResponse(
        agent_wallet=details.wallet,
        alias=details.alias,
        agent_score=details.score,
        trust_tier=details.tier,
        x402_access_policy=details.x402_policy,
        score_components=details.score_components,
        falcon_cert=details.falcon_cert,
        recommendation=recommendation,
        algorand_explorer=details.algorand_explorer_url,
    )


@app.get("/transactions/recent", response_model=RecentTransactionsResponse)
def transactions_recent() -> RecentTransactionsResponse:
    key = "recent_transactions:v1"
    cached = get_cached_json(key, ttl_seconds=5)
    if cached and isinstance(cached.get("transactions"), list):
        return RecentTransactionsResponse.model_validate(cached)

    txs = get_recent_transactions(limit=20)
    payload = RecentTransactionsResponse(transactions=txs)
    set_cached_json(key, payload.model_dump(mode="json"))
    return payload


@app.post("/agents/register", response_model=RegisterAgentResponse)
def register_agent(body: RegisterAgentRequest) -> RegisterAgentResponse:
    if not _alias_valid(body.alias):
        raise HTTPException(
            status_code=400, detail="Alias must be alphanumeric 3-32 chars"
        )

    if not algorand_service.validate_wallet(body.wallet):
        if not body.wallet.startswith("MOCKWALLET"):
            raise HTTPException(
                status_code=400, detail="Invalid Algorand wallet address"
            )

    alias_owner = get_registration_by_alias(body.alias)
    if alias_owner and alias_owner["wallet"] != body.wallet:
        raise HTTPException(status_code=409, detail="Alias already in use")

    available = algorand_service.alias_available(body.alias)
    if not available and not alias_owner:
        raise HTTPException(status_code=409, detail="Alias not available on-chain")

    prior = get_registration(body.wallet)
    tx_id = f"REGISTER_{body.wallet[-8:]}_{int(datetime.now(UTC).timestamp())}"
    registered_at = (
        datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    upsert_registration(
        wallet=body.wallet,
        alias=body.alias,
        collateral=body.collateral,
        register_tx_id=tx_id,
        registered_at=registered_at,
    )

    invalidate_cache("leaderboard:")
    invalidate_cache("agent:")
    invalidate_cache("stats:")

    return RegisterAgentResponse(
        status="updated" if prior else "registered",
        wallet=body.wallet,
        alias=body.alias,
        collateral=body.collateral,
        register_tx_id=tx_id,
        registered_at=registered_at,
    )


@app.post("/record-payment", response_model=RecordPaymentResponse)
def record_payment(body: RecordPaymentRequest) -> RecordPaymentResponse:
    ts = body.timestamp
    timestamp = (
        ts.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        if ts
        else datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    insert_payment_record(
        agent_alias=body.agent_alias,
        agent_wallet=body.agent_wallet,
        service_name=body.service_name,
        amount_usdc=body.amount_usdc,
        success=body.success,
        score_change=body.score_change,
        tx_id=body.tx_id,
        timestamp=timestamp,
    )
    invalidate_cache("recent_transactions:")
    invalidate_cache(f"agent:{body.agent_wallet}")
    invalidate_cache("stats:")
    invalidate_cache("leaderboard:")
    return RecordPaymentResponse(stored=True, tx_id=body.tx_id)


# ──────────────── Activity Log + Dashboard API ────────────────


@app.get("/api/activity-log")
async def api_activity_log(limit: int = Query(default=50, ge=1, le=200)) -> dict:
    """Real-time activity feed for the frontend dashboard."""
    from activity_log import activity_log

    entries = await activity_log.get_recent(limit=limit)
    return {"entries": entries, "count": len(entries)}


@app.get("/api/dashboard")
async def api_dashboard() -> dict:
    """Aggregated dashboard data for the frontend — wallet + transactions + stats."""
    from activity_log import activity_log

    recent_txns = get_recent_transactions(limit=20)
    stats = _load_stats_raw()
    logs = await activity_log.get_recent(limit=30)

    return {
        "stats": stats,
        "recent_transactions": recent_txns,
        "activity_log": logs,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True
    )
