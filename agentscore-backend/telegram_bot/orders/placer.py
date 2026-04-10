from __future__ import annotations

import logging

from telegram_bot.orders import (
    amazon_order,
    flipkart_order,
    instamart_order,
    zepto_order,
)
from telegram_bot.search.models import OrderResult, PlatformResult

logger = logging.getLogger("agentscore.orders.placer")

_DISPATCHERS = {
    "amazon": amazon_order.place,
    "flipkart": flipkart_order.place,
    "zepto": zepto_order.place,
    "instamart": instamart_order.place,
}


async def place_order(
    user_id: int,
    result: PlatformResult,
    delivery_address: dict | None = None,
) -> OrderResult:
    """Route order to the correct platform module."""

    address = delivery_address or {}
    payment: dict = {"user_id": user_id}

    dispatch_fn = _DISPATCHERS.get(result.platform)
    if dispatch_fn is None:
        logger.error("unknown_platform platform=%s", result.platform)
        return OrderResult(
            success=False, error=f"Unsupported platform: {result.platform}"
        )

    try:
        order = await dispatch_fn(result.product_id, address, payment)
        order.amount_charged = result.total_cost
        logger.info(
            "order_placed user=%d platform=%s order_id=%s",
            user_id,
            result.platform,
            order.order_id,
        )
        return order
    except Exception as exc:
        logger.error(
            "order_error user=%d platform=%s error=%s",
            user_id,
            result.platform,
            str(exc)[:200],
        )
        return OrderResult(
            success=False,
            error=f"Order placement failed: {exc}",
        )
