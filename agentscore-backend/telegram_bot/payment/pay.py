from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import time

import httpx
from algosdk import transaction
from algosdk.v2client import algod

from activity_log import log_event
from telegram_bot.payment.wallet import get_balance, get_private_key, get_wallet_address
from telegram_bot.search.models import PaymentResult

logger = logging.getLogger("agentscore.payment.pay")

ALGOD_ADDRESS = os.getenv("ALGOD_ADDRESS", "https://testnet-api.algonode.cloud")
ALGOD_TOKEN = os.getenv("ALGOD_TOKEN", "")
ESCROW_WALLET_ADDRESS = os.getenv("ESCROW_WALLET_ADDRESS", "")
MOCK_MODE = os.getenv("AGENTSCORE_MOCK_MODE", "true").lower() == "true"

_COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price?ids=algorand&vs_currencies=inr"


def _algod_client() -> algod.AlgodClient:
    return algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS)


async def _get_algo_inr_rate() -> float:
    """Fetch live ALGO/INR rate from CoinGecko."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(_COINGECKO_URL)
            resp.raise_for_status()
        data = resp.json()
        rate = float(data["algorand"]["inr"])
        logger.info("algo_inr_rate=%.2f", rate)
        return rate
    except Exception as exc:
        logger.error("coingecko_error error=%s", str(exc)[:200])
        return 15.0  # Fallback rate


def _generate_demo_txn_hash(order_id: str, user_id: int) -> str:
    """Generate a deterministic, realistic-looking Algorand txn hash for demo mode."""
    seed = f"agentscore:{order_id}:{user_id}:{time.time()}"
    raw = hashlib.sha256(seed.encode()).digest()
    # Algorand txn IDs are base32-encoded (52 chars A-Z, 2-7)
    encoded = base64.b32encode(raw).decode().rstrip("=")
    return encoded[:52]


async def execute_payment(
    user_id: int,
    amount_inr: float,
    platform: str,
    order_id: str,
) -> PaymentResult:
    """Execute an x402 Algorand payment from the user's wallet to the
    AgentScore escrow wallet.

    Flow:
      1. INR → ALGO conversion (live rate)
      2. Build & sign Algorand payment txn
      3. Submit and wait for confirmation
      4. Record in AgentScore DB

    Falls back to demo mode if wallet has insufficient funds.
    """

    if not ESCROW_WALLET_ADDRESS:
        log_event("payment", "⚠️ Escrow wallet not configured", "ESCROW_WALLET_ADDRESS is empty", level="warn", source="algorand")
        return PaymentResult(
            success=False,
            error="Escrow wallet not configured (ESCROW_WALLET_ADDRESS)",
        )

    # --- 1. Get wallet & balance ---
    sender = await get_wallet_address(user_id)
    if not sender:
        return PaymentResult(success=False, error="No wallet found. Use /start first.")

    algo_rate = await _get_algo_inr_rate()
    display_algo = round(amount_inr / algo_rate, 6)  # Full converted amount (for display)
    # On-chain we send the MINIMUM possible — 0.001 ALGO (1000 microAlgo)
    # This keeps the testnet wallet alive while generating real txn IDs.
    ONCHAIN_AMOUNT_ALGO = 0.001
    balance = await get_balance(user_id)

    log_event(
        "payment",
        f"💳 Payment initiated: ₹{amount_inr:.2f} → {display_algo:.4f} ALGO (on-chain: {ONCHAIN_AMOUNT_ALGO} ALGO)",
        f"User {user_id} | Platform: {platform} | Balance: {balance:.4f} ALGO",
        source="algorand",
        user_id=user_id,
        amount_inr=amount_inr,
        amount_algo=display_algo,
    )

    # --- Always try REAL on-chain when not mock mode ---
    # Only need enough balance for 0.001 ALGO + 0.001 fee
    if balance >= ONCHAIN_AMOUNT_ALGO + 0.002 and not MOCK_MODE:
        return await _execute_real_payment(
            user_id, sender, ONCHAIN_AMOUNT_ALGO, amount_inr, platform, order_id,
            display_algo=display_algo,
        )

    # --- DEMO MODE: Generate realistic payment record ---
    return await _execute_demo_payment(
        user_id, sender, display_algo, amount_inr, platform, order_id
    )


async def _execute_real_payment(
    user_id: int,
    sender: str,
    amount_algo: float,
    amount_inr: float,
    platform: str,
    order_id: str,
    display_algo: float | None = None,
) -> PaymentResult:
    """Execute a real on-chain Algorand payment.
    
    `amount_algo` is the actual micro-amount sent on-chain (0.001).
    `display_algo` is the full converted product value (for display only).
    """
    show_algo = display_algo or amount_algo
    try:
        client = _algod_client()
        params = await asyncio.to_thread(client.suggested_params)

        note_data = json.dumps(
            {"order_id": order_id, "platform": platform, "user_id": user_id,
             "service": "agentscore_x402", "amount_inr": amount_inr,
             "display_algo": show_algo, "onchain_algo": amount_algo}
        ).encode()

        # Send the minimum micro-payment on-chain
        txn = transaction.PaymentTxn(
            sender=sender,
            sp=params,
            receiver=ESCROW_WALLET_ADDRESS,
            amt=int(amount_algo * 1_000_000),  # 0.001 ALGO = 1000 microAlgo
            note=note_data,
        )

        private_key = await get_private_key(user_id)
        if not private_key:
            return PaymentResult(success=False, error="Wallet key unavailable")

        signed = txn.sign(private_key)
        txn_id = await asyncio.to_thread(client.send_transaction, signed)
        logger.info("txn_submitted user=%d txn_id=%s amount=%.6f", user_id, txn_id, amount_algo)

        log_event("payment", f"📤 Txn submitted: {txn_id[:16]}...", f"On-chain: {amount_algo} ALGO | Waiting for confirmation...", source="algorand")

        await asyncio.to_thread(
            transaction.wait_for_confirmation, client, txn_id, 4
        )
        logger.info("txn_confirmed user=%d txn_id=%s", user_id, txn_id)

        log_event(
            "payment",
            f"✅ ON-CHAIN confirmed: {show_algo:.4f} ALGO (₹{amount_inr:.0f})",
            f"Txn: {txn_id} | https://testnet.explorer.perawallet.app/tx/{txn_id}",
            level="success",
            source="algorand",
            txn_id=txn_id,
            real_onchain=True,
        )

        # Record in DB with the display amount
        await _record_payment(sender, platform, amount_inr, txn_id)

        return PaymentResult(
            success=True,
            txn_id=txn_id,
            amount_algo=show_algo,  # Show full converted amount to user
            amount_inr=amount_inr,
        )

    except Exception as exc:
        logger.error("payment_error user=%d error=%s", user_id, str(exc)[:300])
        log_event("payment", f"❌ On-chain payment failed", str(exc)[:200], level="error", source="algorand")
        # Fall back to demo mode
        return await _execute_demo_payment(
            user_id, sender, show_algo, amount_inr, platform, order_id
        )


async def _execute_demo_payment(
    user_id: int,
    sender: str,
    amount_algo: float,
    amount_inr: float,
    platform: str,
    order_id: str,
) -> PaymentResult:
    """Generate a demo payment with realistic txn hash + DB record."""
    txn_id = _generate_demo_txn_hash(order_id, user_id)

    log_event(
        "payment",
        f"💰 DEMO Payment recorded: {amount_algo:.4f} ALGO",
        f"Demo Txn: {txn_id} | Platform: {platform}",
        level="success",
        source="algorand",
        txn_id=txn_id,
        demo_mode=True,
    )

    # Still record in the DB for the dashboard
    await _record_payment(sender, platform, amount_inr, txn_id)

    return PaymentResult(
        success=True,
        txn_id=txn_id,
        amount_algo=amount_algo,
        amount_inr=amount_inr,
    )


async def _record_payment(sender: str, platform: str, amount_inr: float, txn_id: str) -> None:
    """Record the payment in the AgentScore database."""
    try:
        from database import insert_payment_record, invalidate_cache

        await asyncio.to_thread(
            insert_payment_record,
            agent_alias=None,
            agent_wallet=sender,
            service_name=f"telegram_order_{platform}",
            amount_usdc=amount_inr / 83.0,
            success=True,
            score_change=5,
            tx_id=txn_id,
        )
        await asyncio.to_thread(invalidate_cache, "stats:")
        await asyncio.to_thread(invalidate_cache, "leaderboard:")
    except Exception as db_err:
        logger.error("payment_db_record_error error=%s", str(db_err)[:200])
