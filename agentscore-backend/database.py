from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Generator

DB_PATH = Path(
    os.getenv("AGENTSCORE_DB_PATH", Path(__file__).with_name("agentscore.db"))
)
_DB_LOCK = threading.Lock()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS cache (
                cache_key TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS registrations (
                wallet TEXT PRIMARY KEY,
                alias TEXT UNIQUE NOT NULL,
                collateral REAL NOT NULL DEFAULT 0,
                registered_at TEXT NOT NULL,
                register_tx_id TEXT
            );

            CREATE TABLE IF NOT EXISTS payment_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_alias TEXT,
                agent_wallet TEXT NOT NULL,
                service_name TEXT NOT NULL,
                amount_usdc REAL NOT NULL,
                success INTEGER NOT NULL,
                score_change INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                tx_id TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_payment_wallet_time
            ON payment_history(agent_wallet, timestamp DESC);

            CREATE TABLE IF NOT EXISTS ratings_received (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_wallet TEXT NOT NULL,
                rater_wallet TEXT,
                rating REAL NOT NULL,
                feedback TEXT,
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_ratings_wallet_time
            ON ratings_received(agent_wallet, timestamp DESC);

            CREATE TABLE IF NOT EXISTS score_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_wallet TEXT NOT NULL,
                snapshot_date TEXT NOT NULL,
                score INTEGER NOT NULL,
                UNIQUE(agent_wallet, snapshot_date)
            );

            CREATE INDEX IF NOT EXISTS idx_snapshots_wallet_date
            ON score_snapshots(agent_wallet, snapshot_date DESC);
            """
        )


def utcnow_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def get_cached_json(cache_key: str, ttl_seconds: int) -> dict[str, Any] | None:
    now = int(datetime.now(UTC).timestamp())
    with get_db() as conn:
        row = conn.execute(
            "SELECT payload, updated_at FROM cache WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()

    if not row:
        return None

    if now - int(row["updated_at"]) > ttl_seconds:
        return None

    try:
        return json.loads(row["payload"])
    except json.JSONDecodeError:
        return None


def set_cached_json(cache_key: str, payload: dict[str, Any]) -> None:
    now = int(datetime.now(UTC).timestamp())
    with _DB_LOCK, get_db() as conn:
        conn.execute(
            """
            INSERT INTO cache(cache_key, payload, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(cache_key)
            DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at
            """,
            (cache_key, json.dumps(payload), now),
        )


def invalidate_cache(prefix: str | None = None) -> None:
    with _DB_LOCK, get_db() as conn:
        if prefix:
            conn.execute("DELETE FROM cache WHERE cache_key LIKE ?", (f"{prefix}%",))
        else:
            conn.execute("DELETE FROM cache")


def upsert_registration(
    wallet: str,
    alias: str,
    collateral: float,
    register_tx_id: str | None = None,
    registered_at: str | None = None,
) -> None:
    registered_at = registered_at or utcnow_iso()
    with _DB_LOCK, get_db() as conn:
        conn.execute(
            """
            INSERT INTO registrations(wallet, alias, collateral, registered_at, register_tx_id)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(wallet)
            DO UPDATE SET
                alias=excluded.alias,
                collateral=excluded.collateral,
                registered_at=excluded.registered_at,
                register_tx_id=excluded.register_tx_id
            """,
            (wallet, alias, collateral, registered_at, register_tx_id),
        )


def get_registration(wallet: str) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM registrations WHERE wallet = ?", (wallet,)
        ).fetchone()
    return dict(row) if row else None


def get_registration_by_alias(alias: str) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM registrations WHERE alias = ?", (alias,)
        ).fetchone()
    return dict(row) if row else None


def list_registrations() -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT wallet, alias, collateral, registered_at, register_tx_id FROM registrations"
        ).fetchall()
    return [dict(r) for r in rows]


def insert_payment_record(
    *,
    agent_alias: str | None,
    agent_wallet: str,
    service_name: str,
    amount_usdc: float,
    success: bool,
    score_change: int,
    tx_id: str,
    timestamp: str | None = None,
) -> None:
    timestamp = timestamp or utcnow_iso()
    with _DB_LOCK, get_db() as conn:
        conn.execute(
            """
            INSERT INTO payment_history(
                agent_alias,
                agent_wallet,
                service_name,
                amount_usdc,
                success,
                score_change,
                timestamp,
                tx_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                agent_alias,
                agent_wallet,
                service_name,
                amount_usdc,
                int(success),
                score_change,
                timestamp,
                tx_id,
            ),
        )


def get_recent_transactions(limit: int = 20) -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT agent_alias, agent_wallet, service_name, amount_usdc,
                   success, score_change, timestamp, tx_id
            FROM payment_history
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["success"] = bool(item["success"])
        result.append(item)
    return result


def get_payment_history_for_wallet(
    wallet: str, limit: int = 20
) -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT agent_alias, agent_wallet, service_name, amount_usdc,
                   success, score_change, timestamp, tx_id
            FROM payment_history
            WHERE agent_wallet = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (wallet, limit),
        ).fetchall()

    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["success"] = bool(item["success"])
        result.append(item)
    return result


def get_payment_stats(wallet: str) -> dict[str, Any]:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_count,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) AS success_count,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) AS fail_count,
                COALESCE(SUM(amount_usdc), 0) AS total_volume_usdc
            FROM payment_history
            WHERE agent_wallet = ?
            """,
            (wallet,),
        ).fetchone()

    if not row:
        return {
            "total_count": 0,
            "success_count": 0,
            "fail_count": 0,
            "total_volume_usdc": 0.0,
        }
    return {
        "total_count": int(row["total_count"] or 0),
        "success_count": int(row["success_count"] or 0),
        "fail_count": int(row["fail_count"] or 0),
        "total_volume_usdc": float(row["total_volume_usdc"] or 0),
    }


def insert_rating(
    *,
    agent_wallet: str,
    rater_wallet: str | None,
    rating: float,
    feedback: str | None,
    timestamp: str | None = None,
) -> None:
    timestamp = timestamp or utcnow_iso()
    with _DB_LOCK, get_db() as conn:
        conn.execute(
            """
            INSERT INTO ratings_received(agent_wallet, rater_wallet, rating, feedback, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (agent_wallet, rater_wallet, rating, feedback, timestamp),
        )


def get_ratings_for_wallet(wallet: str, limit: int = 20) -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT agent_wallet, rater_wallet, rating, feedback, timestamp
            FROM ratings_received
            WHERE agent_wallet = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (wallet, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_rating_stats(wallet: str) -> dict[str, Any]:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS total_ratings, COALESCE(AVG(rating), 0) AS avg_rating
            FROM ratings_received
            WHERE agent_wallet = ?
            """,
            (wallet,),
        ).fetchone()

    if not row:
        return {"total_ratings": 0, "avg_rating": 0.0}
    return {
        "total_ratings": int(row["total_ratings"] or 0),
        "avg_rating": float(row["avg_rating"] or 0.0),
    }


def upsert_score_snapshot(
    wallet: str, score: int, snapshot_date: str | None = None
) -> None:
    snapshot_date = snapshot_date or datetime.now(UTC).date().isoformat()
    with _DB_LOCK, get_db() as conn:
        conn.execute(
            """
            INSERT INTO score_snapshots(agent_wallet, snapshot_date, score)
            VALUES (?, ?, ?)
            ON CONFLICT(agent_wallet, snapshot_date)
            DO UPDATE SET score = excluded.score
            """,
            (wallet, snapshot_date, score),
        )


def get_score_timeline(wallet: str, days: int = 30) -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT snapshot_date, score
            FROM score_snapshots
            WHERE agent_wallet = ?
            ORDER BY snapshot_date DESC
            LIMIT ?
            """,
            (wallet, days),
        ).fetchall()

    return [
        {
            "date": row["snapshot_date"],
            "score": int(row["score"]),
        }
        for row in reversed(rows)
    ]
