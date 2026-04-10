from __future__ import annotations

import hashlib
import logging
import os
import random

import httpx

from telegram_bot.search.models import PlatformResult

logger = logging.getLogger("agentscore.search.zepto")

ZEPTO_STORE_ID = os.getenv("ZEPTO_STORE_ID", "")

_USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 Chrome/125.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
]


async def _ddg_fallback(query: str) -> list[PlatformResult]:
    from telegram_bot.search.ddg_search import fetch_real_results
    return await fetch_real_results("zepto", query)


async def search(query: str) -> list[PlatformResult]:
    """Search Zepto for *query*. Uses internal API with browser headers."""

    if not ZEPTO_STORE_ID:
        logger.info("zepto_ddg query=%s (no store ID)", query)
        return await _ddg_fallback(query)

    try:
        headers = {
            "User-Agent": random.choice(_USER_AGENTS),
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-store-id": ZEPTO_STORE_ID,
            "appVersion": "16.48.0",
            "Origin": "https://www.zeptonow.com",
            "Referer": "https://www.zeptonow.com/",
        }

        payload = {
            "query": query,
            "pageNumber": 0,
            "mode": "AUTOSUGGEST",
        }

        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                "https://api.zeptonow.com/api/v3/search",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()

        data = resp.json()
        items = data.get("data", {}).get("items", [])
        results: list[PlatformResult] = []

        for item in items[:3]:
            product = item.get("product", item)
            mrp = float(product.get("mrp", 0)) / 100
            selling = float(product.get("sellingPrice", product.get("offer_price", 0))) / 100

            disc = None
            if mrp > selling > 0:
                disc = round((1 - selling / mrp) * 100, 1)

            pid = str(product.get("id", product.get("productId", "")))
            results.append(
                PlatformResult(
                    platform="zepto",
                    product_name=product.get("name", query),
                    price=selling if selling > 0 else mrp,
                    original_price=mrp if mrp > selling else None,
                    discount_percent=disc,
                    delivery_time="10 mins",
                    delivery_fee=0.0,
                    product_url=f"https://www.zeptonow.com/pn/{pid}",
                    product_id=pid,
                    image_url=product.get("image", None),
                    in_stock=product.get("inStock", True),
                    rating=None,
                    review_count=None,
                )
            )

        logger.info("zepto_search_ok query=%s results=%d", query, len(results))
        return results

    except Exception as exc:
        logger.error("zepto_search_error query=%s error=%s", query, str(exc)[:200])
        return await _ddg_fallback(query)
