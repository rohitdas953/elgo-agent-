from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from telegram_bot.handlers import (
    cancel_handler,
    help_handler,
    photo_handler,
    start_handler,
    text_handler,
    wallet_handler,
)
from telegram_bot.session import session_manager

logger = logging.getLogger("agentscore.bot")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "")

router = APIRouter(tags=["telegram"])

# Module-level application reference — initialized in setup_bot()
_application: Application | None = None


def _build_application() -> Application:
    """Build the python-telegram-bot Application with all handlers."""
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN env var is not set")

    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    # Command handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("wallet", wallet_handler))
    app.add_handler(CommandHandler("cancel", cancel_handler))

    # Photo handler
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    # Text handler (numbers, YES, cancel, etc.)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    return app


async def setup_bot() -> None:
    """Initialize the bot application and register the webhook with Telegram."""
    global _application

    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set — bot disabled")
        return

    _application = _build_application()

    # Initialize the application (sets up bot, updater, etc.)
    await _application.initialize()
    await _application.start()

    # Start session cleanup loop
    await session_manager.start_cleanup_loop()

    # Register webhook with Telegram
    webhook_url = f"{WEBHOOK_BASE_URL}/telegram/webhook" if WEBHOOK_BASE_URL else ""
    if webhook_url:
        await _application.bot.set_webhook(
            url=webhook_url,
            allowed_updates=["message"],
        )
        logger.info("webhook_registered url=%s", webhook_url)
    else:
        logger.warning("WEBHOOK_BASE_URL not set — starting polling mode")
        await _application.bot.delete_webhook(drop_pending_updates=True)
        await _application.updater.start_polling()


async def shutdown_bot() -> None:
    """Gracefully shut down the bot."""
    global _application

    await session_manager.stop_cleanup_loop()

    if _application:
        try:
            if _application.updater and _application.updater.running:
                await _application.updater.stop()
            await _application.stop()
            await _application.shutdown()
        except Exception as e:
            logger.warning("Error shutting down bot: %s", e)
        _application = None
        logger.info("bot_shutdown")


# ──────────────────── FastAPI Webhook Route ────────────────────


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request) -> JSONResponse:
    """Receive Telegram webhook updates and process them."""
    if _application is None:
        return JSONResponse(
            {"error": "Bot not initialized"}, status_code=503
        )

    try:
        data = await request.json()
        update = Update.de_json(data, _application.bot)
        await _application.process_update(update)
        return JSONResponse({"ok": True})
    except Exception as exc:
        logger.error("webhook_error error=%s", str(exc)[:300])
        return JSONResponse({"ok": False, "error": str(exc)[:100]}, status_code=500)


# ──────────────────── REST API Routes ─────────────────────────


@router.get("/user/{telegram_id}/wallet")
async def get_user_wallet(telegram_id: int) -> dict[str, Any]:
    """Get wallet address + balance for a Telegram user."""
    from telegram_bot.payment.wallet import get_balance, get_or_create_wallet

    wallet = await get_or_create_wallet(telegram_id)
    balance = await get_balance(telegram_id)
    return {
        "telegram_id": telegram_id,
        "wallet_address": wallet["address"],
        "balance_algo": balance,
        "created_at": wallet["created_at"],
    }


@router.post("/user/{telegram_id}/search")
async def manual_search(telegram_id: int, request: Request) -> dict[str, Any]:
    """Manual search endpoint for dashboard + testing."""
    body = await request.json()
    query = body.get("query", "")
    category = body.get("category", "other")
    is_grocery = body.get("is_grocery", False)

    if not query:
        return {"error": "query is required"}

    from activity_log import log_event
    from telegram_bot.search.aggregator import search_all_platforms

    log_event("search", f"🔍 Web search: {query}", f"Category: {category} | Grocery: {is_grocery}", source="search", user_id=telegram_id)

    results = await search_all_platforms(query, category, is_grocery)

    log_event(
        "search",
        f"✅ Found {len(results)} results for '{query}'",
        f"Platforms: {', '.join(set(r.platform for r in results))}",
        level="success",
        source="search",
        results_count=len(results),
    )

    return {
        "query": query,
        "results": [r.model_dump() for r in results],
    }


@router.get("/user/{telegram_id}/orders")
async def get_user_orders(telegram_id: int) -> dict[str, Any]:
    """Get order history for a Telegram user."""
    import asyncio

    from telegram_bot.payment.wallet import get_wallet_address
    from database import get_payment_history_for_wallet

    address = await get_wallet_address(telegram_id)
    if not address:
        return {"telegram_id": telegram_id, "orders": []}

    history = await asyncio.to_thread(get_payment_history_for_wallet, address, 50)
    return {"telegram_id": telegram_id, "orders": history}
