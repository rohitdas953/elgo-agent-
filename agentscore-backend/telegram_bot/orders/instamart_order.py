from __future__ import annotations

import logging

from telegram_bot.search.models import OrderResult

logger = logging.getLogger("agentscore.orders.instamart")


async def place(product_id: str, address: dict, payment: dict) -> OrderResult:
    """Place an order on Swiggy Instamart.

    Production: POST /order/place using stored Swiggy session.
    Demo: Simulated success.
    """
    logger.info("instamart_order product_id=%s", product_id)

    return OrderResult(
        success=True,
        order_id=f"IM-{product_id[-8:]}-DEMO",
        estimated_delivery="15-20 minutes",
        tracking_url=f"https://www.swiggy.com/my-account/orders",
        amount_charged=0.0,
        error=None,
    )
