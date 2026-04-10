from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

from database import (
    get_payment_stats,
    get_rating_stats,
    get_registration,
    upsert_score_snapshot,
)


class ScoreService:
    def __init__(self) -> None:
        pass

    @staticmethod
    def tier_from_score(score: int) -> str:
        if score >= 800:
            return "PLATINUM"
        if score >= 600:
            return "GOLD"
        if score >= 400:
            return "SILVER"
        if score >= 200:
            return "BRONZE"
        return "STARTER"

    @staticmethod
    def x402_policy_for_score(score: int, collateral_usdc: float) -> dict[str, Any]:
        if score >= 800:
            return {
                "session_access": True,
                "max_session_value_usdc": 200,
                "collateral_required_usdc": 0,
                "payment_mode": "session",
            }
        if score >= 600:
            return {
                "session_access": True,
                "max_session_value_usdc": 100,
                "collateral_required_usdc": max(0.0, 5.0 - collateral_usdc),
                "payment_mode": "session",
            }
        if score >= 400:
            return {
                "session_access": True,
                "max_session_value_usdc": 40,
                "collateral_required_usdc": max(0.0, 10.0 - collateral_usdc),
                "payment_mode": "hybrid",
            }
        return {
            "session_access": False,
            "max_session_value_usdc": 0,
            "collateral_required_usdc": max(0.0, 15.0 - collateral_usdc),
            "payment_mode": "per_request",
        }

    def compute_components(
        self,
        wallet: str,
        base_transaction_count: int,
        fallback_collateral: float = 0.0,
        registered_date: str | None = None,
    ) -> dict[str, Any]:
        payment = get_payment_stats(wallet)
        rating = get_rating_stats(wallet)
        registration = get_registration(wallet)

        collateral = (
            float(registration["collateral"])
            if registration
            else float(fallback_collateral)
        )

        reg_date_str = registered_date
        if registration and registration.get("registered_at"):
            reg_date_str = str(registration["registered_at"])[:10]

        if reg_date_str:
            parsed = datetime.fromisoformat(reg_date_str.replace("Z", "+00:00"))
            reg_date = parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
            age_days = max(1, (datetime.now(UTC) - reg_date).days)
        else:
            age_days = 1

        payment_success_count = int(payment["success_count"])
        payment_fail_count = int(payment["fail_count"])
        payment_total = payment_success_count + payment_fail_count
        payment_success_rate = (
            payment_success_count / payment_total if payment_total > 0 else 1.0
        )

        transaction_count = max(
            int(base_transaction_count), int(payment["total_count"])
        )
        avg_rating = float(rating["avg_rating"])
        total_ratings = int(rating["total_ratings"])

        return {
            "payment_success_rate": round(payment_success_rate, 4),
            "payment_success_count": payment_success_count,
            "payment_fail_count": payment_fail_count,
            "avg_rating": round(avg_rating, 2),
            "total_ratings": total_ratings,
            "transaction_count": transaction_count,
            "collateral_staked_usdc": round(collateral, 3),
            "account_age_days": age_days,
        }

    def compute_score(self, components: dict[str, Any], base_score: int = 0) -> int:
        success_rate = float(components["payment_success_rate"])
        tx_count = int(components["transaction_count"])
        avg_rating = float(components["avg_rating"])
        total_ratings = int(components["total_ratings"])
        collateral = float(components["collateral_staked_usdc"])
        age_days = int(components["account_age_days"])

        tx_factor = min(1.0, math.log1p(tx_count) / math.log(101))
        rating_factor = min(
            1.0, (avg_rating / 5.0) * (1 - math.exp(-total_ratings / 20))
        )
        collateral_factor = min(1.0, collateral / 20)
        age_factor = min(1.0, age_days / 90)

        blended = (
            success_rate * 0.35
            + tx_factor * 0.2
            + rating_factor * 0.25
            + collateral_factor * 0.1
            + age_factor * 0.1
        )

        computed = int(round(blended * 1000))
        if base_score > 0:
            computed = int(round((computed * 0.75) + (base_score * 0.25)))

        return max(0, min(1000, computed))

    def persist_snapshot(self, wallet: str, score: int) -> None:
        upsert_score_snapshot(wallet, score)

    def recommendation_for_tier(self, tier: str) -> str:
        if tier == "PLATINUM":
            return "ALLOW — High-trust agent. Grant full session access."
        if tier == "GOLD":
            return "ALLOW WITH LIMITS — Trusted agent. Keep moderate session cap."
        if tier == "SILVER":
            return "REVIEW — Medium trust. Use tighter spending controls."
        if tier == "BRONZE":
            return "LIMITED — Low trust. Require collateral and strict caps."
        return "DENY SESSION — Very low trust. Allow per-request only."
