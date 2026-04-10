from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from algosdk import account, mnemonic
from algosdk.v2client import algod
from cryptography.fernet import Fernet

from database import get_db, _DB_LOCK

logger = logging.getLogger("agentscore.payment.wallet")

WALLET_ENCRYPTION_KEY = os.getenv("WALLET_ENCRYPTION_KEY", "")
ALGOD_ADDRESS = os.getenv("ALGOD_ADDRESS", "https://testnet-api.algonode.cloud")
ALGOD_TOKEN = os.getenv("ALGOD_TOKEN", "")


def _fernet() -> Fernet:
    """Derive a valid Fernet cipher from the WALLET_ENCRYPTION_KEY env var."""
    import base64
    import hashlib

    raw = WALLET_ENCRYPTION_KEY.encode("utf-8") if WALLET_ENCRYPTION_KEY else b"default_dev_key"
    # SHA-256 produces 32 bytes; Fernet needs 32 url-safe base64-encoded bytes
    key = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    return Fernet(key)


def _algod_client() -> algod.AlgodClient:
    return algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS)


def _ensure_wallet_table() -> None:
    """Create the user_wallets table if it doesn't exist."""
    with _DB_LOCK, get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_wallets (
                telegram_user_id INTEGER PRIMARY KEY,
                wallet_address TEXT NOT NULL,
                encrypted_mnemonic TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


# Run once on import
_ensure_wallet_table()


def _store_wallet(
    telegram_user_id: int, address: str, encrypted_mn: str, created_at: str
) -> None:
    with _DB_LOCK, get_db() as conn:
        conn.execute(
            """
            INSERT INTO user_wallets(telegram_user_id, wallet_address, encrypted_mnemonic, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_user_id) DO NOTHING
            """,
            (telegram_user_id, address, encrypted_mn, created_at),
        )


def _get_wallet_row(telegram_user_id: int) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT wallet_address, encrypted_mnemonic, created_at FROM user_wallets WHERE telegram_user_id = ?",
            (telegram_user_id,),
        ).fetchone()
    return dict(row) if row else None


async def get_or_create_wallet(telegram_user_id: int) -> dict[str, Any]:
    """Return existing wallet or generate a new Algorand account for the user."""

    existing = await asyncio.to_thread(_get_wallet_row, telegram_user_id)
    if existing:
        return {
            "address": existing["wallet_address"],
            "created_at": existing["created_at"],
        }

    # Generate fresh Algorand account
    private_key, address = account.generate_account()
    mn = mnemonic.from_private_key(private_key)

    # Encrypt mnemonic
    f = _fernet()
    encrypted = f.encrypt(mn.encode()).decode("ascii")

    from database import utcnow_iso

    created_at = utcnow_iso()
    await asyncio.to_thread(_store_wallet, telegram_user_id, address, encrypted, created_at)

    logger.info("wallet_created user=%d address=%s", telegram_user_id, address)
    return {"address": address, "created_at": created_at}


async def get_wallet_address(telegram_user_id: int) -> str | None:
    """Get the wallet address for a user, or None if not yet created."""
    row = await asyncio.to_thread(_get_wallet_row, telegram_user_id)
    return row["wallet_address"] if row else None


async def get_private_key(telegram_user_id: int) -> str | None:
    """Decrypt and return the user's private key. NEVER log this."""
    row = await asyncio.to_thread(_get_wallet_row, telegram_user_id)
    if not row:
        return None

    f = _fernet()
    mn = f.decrypt(row["encrypted_mnemonic"].encode()).decode()
    return mnemonic.to_private_key(mn)


async def get_balance(telegram_user_id: int) -> float:
    """Get ALGO balance for the user's wallet."""
    address = await get_wallet_address(telegram_user_id)
    if not address:
        return 0.0

    try:
        client = _algod_client()
        info = await asyncio.to_thread(client.account_info, address)
        micro_algos = info.get("amount", 0)
        return micro_algos / 1_000_000
    except Exception as exc:
        logger.error("balance_check_error user=%d error=%s", telegram_user_id, str(exc)[:200])
        return 0.0


async def top_up_instructions(telegram_user_id: int) -> str:
    """Return formatted top-up instructions for the user."""
    wallet = await get_or_create_wallet(telegram_user_id)
    address = wallet["address"]

    return (
        f"💳 *Your AgentScore Wallet*\n\n"
        f"Address:\n`{address}`\n\n"
        f"Send ALGO to this address on Algorand Testnet.\n"
        f"Your balance will update automatically."
    )
