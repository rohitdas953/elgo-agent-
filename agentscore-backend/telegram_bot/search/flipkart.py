from __future__ import annotations

import hashlib
import logging
import os
import random

import httpx

from telegram_bot.search.models import PlatformResult

logger = logging.getLogger("agentscore.search.flipkart")

FLIPKART_AFFILIATE_ID = os.getenv("FLIPKART_AFFILIATE_ID", "")
FLIPKART_TOKEN = os.getenv("FLIPKART_TOKEN", "")

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 Safari/605.1.15",
]


async def _ddg_fallback(query: str) -> list[PlatformResult]:
    from telegram_bot.search.ddg_search import fetch_real_results
    return await fetch_real_results("flipkart", query)


async def search(query: str) -> list[PlatformResult]:
    """Search Flipkart for *query*."""

    if not FLIPKART_AFFILIATE_ID:
        logger.info("flipkart_ddg query=%s (no affiliate ID)", query)
        return await _ddg_fallback(query)

    try:
        url = (
            f"https://affiliate-api.flipkart.net/affiliate/1.0/search.json"
            f"?query={query}&resultCount=3"
        )
        headers = {
            "Fk-Affiliate-Id": FLIPKART_AFFILIATE_ID,
            "Fk-Affiliate-Token": FLIPKART_TOKEN,
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()

        data = resp.json()
        products = data.get("products", [])
        results: list[PlatformResult] = []

        for item in products[:3]:
            product_base = item.get("productBaseInfoV1", {})
            price_map = product_base.get("flipkartSpecialPrice", {}) or product_base.get("flipkartSellingPrice", {})
            mrp_map = product_base.get("maximumRetailPrice", {})

            price_val = float(price_map.get("amount", 0))
            orig_val = float(mrp_map.get("amount", 0)) if mrp_map else None

            disc = None
            if orig_val and price_val and orig_val > price_val:
                disc = round((1 - price_val / orig_val) * 100, 1)

            results.append(
                PlatformResult(
                    platform="flipkart",
                    product_name=product_base.get("title", query),
                    price=price_val,
                    original_price=orig_val,
                    discount_percent=disc,
                    delivery_time="2-3 days",
                    delivery_fee=0.0 if price_val > 499 else 40.0,
                    product_url=product_base.get("productUrl", ""),
                    product_id=product_base.get("productId", ""),
                    image_url=next(iter(product_base.get("imageUrls", {}).values()), None),
                    in_stock=product_base.get("inStock", True),
                    rating=None,
                    review_count=None,
                )
            )

        logger.info("flipkart_search_ok query=%s results=%d", query, len(results))
        return results

    except Exception as exc:
        logger.error("flipkart_search_error query=%s error=%s", query, str(exc)[:200])
        return await _ddg_fallback(query)
