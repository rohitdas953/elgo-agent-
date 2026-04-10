from __future__ import annotations

import logging

from telegram_bot.search.models import OrderResult

logger = logging.getLogger("agentscore.orders.zepto")


async def place(product_id: str, address: dict, payment: dict) -> OrderResult:
    """Place an order on Zepto.

    Production: POST /cart/add → POST /checkout → POST /order/place
    using stored Zepto session cookies.
    Demo: Simulated success.
    """
    logger.info("zepto_order product_id=%s", product_id)

    return OrderResult(
        success=True,
        order_id=f"ZEP-{product_id[-8:]}-DEMO",
        estimated_delivery="10 minutes",
        tracking_url=f"https://www.zeptonow.com/account/orders",
        amount_charged=0.0,
        error=None,
    )
