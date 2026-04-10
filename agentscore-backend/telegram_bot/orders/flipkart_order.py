from __future__ import annotations

import logging

from telegram_bot.search.models import OrderResult

logger = logging.getLogger("agentscore.orders.flipkart")


async def place(product_id: str, address: dict, payment: dict) -> OrderResult:
    """Place an order on Flipkart.

    Production: Uses playwright headless browser —
      1. Open product deep link
      2. Add to cart
      3. Apply address
      4. Redirect payment to x402 via pay.py
    Demo: Simulated success.
    """
    logger.info("flipkart_order product_id=%s", product_id)

    return OrderResult(
        success=True,
        order_id=f"FK-{product_id[-8:]}-DEMO",
        estimated_delivery="3-5 business days",
        tracking_url=f"https://www.flipkart.com/account/orders",
        amount_charged=0.0,
        error=None,
    )
