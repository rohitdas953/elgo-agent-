from __future__ import annotations

import hashlib
import logging
import os
import random

import httpx

from telegram_bot.search.models import PlatformResult

logger = logging.getLogger("agentscore.search.instamart")

INSTAMART_LAT = os.getenv("INSTAMART_LAT", "")
INSTAMART_LNG = os.getenv("INSTAMART_LNG", "")
INSTAMART_COOKIES = os.getenv("INSTAMART_COOKIES", "")

_USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 Chrome/125.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
]


async def _ddg_fallback(query: str) -> list[PlatformResult]:
    from telegram_bot.search.ddg_search import fetch_real_results
    return await fetch_real_results("instamart", query)


async def search(query: str) -> list[PlatformResult]:
    """Search Swiggy Instamart for *query*."""

    if not INSTAMART_LAT or not INSTAMART_COOKIES:
        logger.info("instamart_ddg query=%s (no config)", query)
        return await _ddg_fallback(query)

    try:
        headers = {
            "User-Agent": random.choice(_USER_AGENTS),
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cookie": INSTAMART_COOKIES,
            "Origin": "https://www.swiggy.com",
            "Referer": "https://www.swiggy.com/instamart",
        }

        url = (
            f"https://www.swiggy.com/api/instamart/search"
            f"?pageNumber=0&searchResultsOffset=0"
            f"&query={query}&ageConsent=false"
            f"&layoutId=2569&pageType=INSTAMART_SEARCH_PAGE"
            f"&lat={INSTAMART_LAT}&lng={INSTAMART_LNG}"
        )

        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()

        data = resp.json()
        widgets = data.get("data", {}).get("widgets", [])

        products_raw: list[dict] = []
        for widget in widgets:
            for item in widget.get("data", []):
                if "variations" in item:
                    for var in item["variations"]:
                        products_raw.append(var)
                elif "price" in item or "mrp" in item:
                    products_raw.append(item)

        results: list[PlatformResult] = []
        for product in products_raw[:3]:
            mrp = float(product.get("mrp", 0))
            price = float(product.get("price", mrp))

            disc = None
            if mrp > price > 0:
                disc = round((1 - price / mrp) * 100, 1)

            pid = str(product.get("id", product.get("product_id", "")))
            results.append(
                PlatformResult(
                    platform="instamart",
                    product_name=product.get("display_name", product.get("name", query)),
                    price=price,
                    original_price=mrp if mrp > price else None,
                    discount_percent=disc,
                    delivery_time="15-20 mins",
                    delivery_fee=0.0,
                    product_url=f"https://www.swiggy.com/instamart/item/{pid}",
                    product_id=pid,
                    image_url=product.get("images", [None])[0] if product.get("images") else None,
                    in_stock=product.get("inStock", True),
                    rating=None,
                    review_count=None,
                )
            )

        logger.info("instamart_search_ok query=%s results=%d", query, len(results))
        return results

    except Exception as exc:
        logger.error("instamart_search_error query=%s error=%s", query, str(exc)[:200])
        return await _ddg_fallback(query)
