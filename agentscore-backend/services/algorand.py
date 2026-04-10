from __future__ import annotations

import base64
import os
import random
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from algosdk.encoding import is_valid_address
from algosdk.v2client import algod, indexer


def _normalize_env_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class AlgorandConfig:
    algod_address: str
    algod_token: str
    indexer_address: str
    indexer_token: str
    app_id: int
    usdc_asa_id: int
    explorer_base_url: str
    mock_mode: bool


def load_config() -> AlgorandConfig:
    return AlgorandConfig(
        algod_address=os.getenv("ALGOD_ADDRESS", "https://testnet-api.algonode.cloud"),
        algod_token=os.getenv("ALGOD_TOKEN", ""),
        indexer_address=os.getenv(
            "INDEXER_ADDRESS", "https://testnet-idx.algonode.cloud"
        ),
        indexer_token=os.getenv("INDEXER_TOKEN", ""),
        app_id=int(os.getenv("AGENTSCORE_APP_ID", "0")),
        usdc_asa_id=int(os.getenv("AGENTSCORE_USDC_ASA_ID", "0")),
        explorer_base_url=os.getenv(
            "ALGORAND_EXPLORER_BASE",
            "https://testnet.explorer.perawallet.app/address",
        ),
        mock_mode=_normalize_env_bool(os.getenv("AGENTSCORE_MOCK_MODE"), default=True),
    )


class AlgorandService:
    def __init__(self) -> None:
        self.config = load_config()
        self.algod_client = algod.AlgodClient(
            self.config.algod_token, self.config.algod_address
        )
        self.indexer_client = indexer.IndexerClient(
            self.config.indexer_token,
            self.config.indexer_address,
        )

    def validate_wallet(self, wallet: str) -> bool:
        return is_valid_address(wallet)

    def explorer_url(self, wallet: str) -> str:
        return f"{self.config.explorer_base_url}/{wallet}"

    def _decode_state(self, state: list[dict[str, Any]] | None) -> dict[str, Any]:
        output: dict[str, Any] = {}
        if not state:
            return output

        for item in state:
            key_b64 = item.get("key")
            if not key_b64:
                continue
            try:
                key = base64.b64decode(key_b64).decode("utf-8")
            except Exception:
                continue

            value = item.get("value", {})
            value_type = value.get("type")
            if value_type == 1:
                bytes_val = value.get("bytes", "")
                try:
                    decoded = base64.b64decode(bytes_val).decode("utf-8")
                except Exception:
                    decoded = bytes_val
                output[key] = decoded
            else:
                output[key] = int(value.get("uint", 0))

        return output

    def get_global_stats(self) -> dict[str, Any]:
        if self.config.mock_mode or self.config.app_id <= 0:
            return {
                "total_agents": 142,
                "total_transactions": 3847,
                "total_collateral_usdc": 892.5,
                "avg_score": 487,
                "weekly_agent_growth": 12.3,
            }

        app = self.algod_client.application_info(self.config.app_id)
        params = app.get("params", {})
        global_state = self._decode_state(params.get("global-state"))

        return {
            "total_agents": int(global_state.get("total_agents", 0)),
            "total_transactions": int(global_state.get("total_transactions", 0)),
            "total_collateral_usdc": float(global_state.get("total_collateral_usdc", 0))
            / 1_000_000,
            "avg_score": int(global_state.get("avg_score", 0)),
            "weekly_agent_growth": float(global_state.get("weekly_agent_growth", 0)),
        }

    def _mock_agents(self) -> list[dict[str, Any]]:
        base_date = datetime(2026, 3, 1, tzinfo=UTC)
        rng = random.Random(42)  # deterministic seed for consistency
        agents: list[dict[str, Any]] = []
        for idx in range(1, 143):
            score = max(50, 900 - idx * 4 + (idx % 7) * 3)
            alias = f"ResearchBot{idx:03d}"
            wallet = f"MOCKWALLET{idx:03d}".ljust(58, "A")
            joined = (base_date.date()).isoformat()
            tiers = self.score_to_tier(score)
            agents.append(
                {
                    "alias": alias,
                    "wallet": wallet,
                    "score": score,
                    "tier": tiers,
                    "transactions": rng.randint(15, 170),
                    "joined_date": joined,
                    "asa_id": self.config.usdc_asa_id or 123456789,
                    "registered_date": joined,
                }
            )
        return sorted(agents, key=lambda a: a["score"], reverse=True)

    def score_to_tier(self, score: int) -> str:
        if score >= 800:
            return "PLATINUM"
        if score >= 600:
            return "GOLD"
        if score >= 400:
            return "SILVER"
        if score >= 200:
            return "BRONZE"
        return "STARTER"

    def get_leaderboard(self) -> list[dict[str, Any]]:
        if self.config.mock_mode or self.config.app_id <= 0:
            return self._mock_agents()

        next_token: str | None = None
        rows: list[dict[str, Any]] = []
        rank_seed = 0

        while True:
            response = self.indexer_client.accounts(
                application_id=self.config.app_id,
                limit=1000,
                next_page=next_token,
            )
            accounts = response.get("accounts", [])

            for acct in accounts:
                wallet = acct.get("address")
                local_states = acct.get("apps-local-state", [])
                local = next(
                    (
                        item
                        for item in local_states
                        if item.get("id") == self.config.app_id
                    ),
                    None,
                )
                if not local:
                    continue

                kv = self._decode_state(local.get("key-value"))
                score = int(kv.get("score", 0))
                alias = str(kv.get("alias", f"agent-{rank_seed}"))
                transactions = int(kv.get("transaction_count", 0))
                joined_raw = int(kv.get("registered_at", 0))
                joined_date = (
                    datetime.fromtimestamp(joined_raw, tz=UTC).date().isoformat()
                    if joined_raw > 0
                    else datetime.now(UTC).date().isoformat()
                )

                rows.append(
                    {
                        "alias": alias,
                        "wallet": wallet,
                        "score": score,
                        "tier": self.score_to_tier(score),
                        "transactions": transactions,
                        "joined_date": joined_date,
                        "asa_id": int(kv.get("asa_id", self.config.usdc_asa_id or 0)),
                        "registered_date": joined_date,
                    }
                )
                rank_seed += 1

            next_token = response.get("next-token")
            if not next_token:
                break

        rows.sort(key=lambda item: item["score"], reverse=True)
        return rows

    def get_agent(self, wallet: str) -> dict[str, Any] | None:
        leaderboard = self.get_leaderboard()
        for item in leaderboard:
            if item["wallet"] == wallet:
                return item

        if self.config.mock_mode:
            return None

        if self.config.app_id <= 0:
            return None

        try:
            result = self.algod_client.account_application_info(
                wallet, self.config.app_id
            )
            local_state = result.get("app-local-state", {})
            kv = self._decode_state(local_state.get("key-value"))
            score = int(kv.get("score", 0))
            joined_raw = int(kv.get("registered_at", 0))
            joined_date = (
                datetime.fromtimestamp(joined_raw, tz=UTC).date().isoformat()
                if joined_raw > 0
                else datetime.now(UTC).date().isoformat()
            )
            return {
                "alias": str(kv.get("alias", wallet[:8])),
                "wallet": wallet,
                "score": score,
                "tier": self.score_to_tier(score),
                "transactions": int(kv.get("transaction_count", 0)),
                "joined_date": joined_date,
                "registered_date": joined_date,
                "asa_id": int(kv.get("asa_id", self.config.usdc_asa_id or 0)),
            }
        except Exception:
            return None

    def alias_available(self, alias: str) -> bool:
        if not re.fullmatch(r"[A-Za-z0-9]{3,32}", alias):
            return False

        if self.config.mock_mode or self.config.app_id <= 0:
            return True

        try:
            self.indexer_client.application_box_by_name(
                self.config.app_id, alias.encode("utf-8")
            )
            return False
        except Exception:
            return True

    def get_asa_for_wallet(self, wallet: str) -> int:
        if self.config.usdc_asa_id > 0:
            return self.config.usdc_asa_id

        if self.config.mock_mode:
            return 123456789

        try:
            info = self.indexer_client.account_info(wallet)
            assets = info.get("account", {}).get("assets", [])
            if assets:
                return int(assets[0].get("asset-id", 0))
        except Exception:
            pass
        return 0
