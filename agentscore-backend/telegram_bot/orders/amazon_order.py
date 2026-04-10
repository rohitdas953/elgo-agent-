from __future__ import annotations

import logging

from telegram_bot.search.models import OrderResult

logger = logging.getLogger("agentscore.orders.amazon")


async def place(product_id: str, address: dict, payment: dict) -> OrderResult:
    """Place an order on Amazon via PA-API / stored credentials.

    In production this would use the Amazon PA-API cart operations
    or a headless browser with pre-stored session cookies.
    For the hackathon demo, returns a simulated success.
    """
    logger.info("amazon_order product_id=%s", product_id)

    # TODO: real implementation with amazon-paapi cart operations
    # or playwright-based checkout flow

    return OrderResult(
        success=True,
        order_id=f"AMZ-{product_id[-8:]}-DEMO",
        estimated_delivery="2-3 business days",
        tracking_url=f"https://www.amazon.in/gp/your-account/order-history",
        amount_charged=0.0,
        error=None,
    )
