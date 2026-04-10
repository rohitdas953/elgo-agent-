from __future__ import annotations

import hashlib
import logging
import os
import random

import httpx

from telegram_bot.search.models import PlatformResult

logger = logging.getLogger("agentscore.search.amazon")

AMAZON_ACCESS_KEY = os.getenv("AMAZON_ACCESS_KEY", "")
AMAZON_SECRET_KEY = os.getenv("AMAZON_SECRET_KEY", "")
AMAZON_PARTNER_TAG = os.getenv("AMAZON_PARTNER_TAG", "")

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
]


async def _ddg_fallback(query: str) -> list[PlatformResult]:
    """Fetch real results via DuckDuckGo when API keys are absent."""
    from telegram_bot.search.ddg_search import fetch_real_results
    return await fetch_real_results("amazon", query)


async def search(query: str) -> list[PlatformResult]:
    """Search Amazon India for *query*. Falls back to mock data
    when AMAZON_ACCESS_KEY is not configured."""

    if not AMAZON_ACCESS_KEY:
        logger.info("amazon_ddg query=%s (no API key)", query)
        return await _ddg_fallback(query)

    # --- Real PA-API v5 integration ---
    try:
        from amazon_paapi import AmazonApi  # type: ignore[import-untyped]

        api = AmazonApi(
            AMAZON_ACCESS_KEY,
            AMAZON_SECRET_KEY,
            AMAZON_PARTNER_TAG,
            country="IN",
        )
        items = api.search_items(keywords=query, item_count=3)
        results: list[PlatformResult] = []
        for item in items.items or []:
            price_val = 0.0
            orig_val = None
            if item.offers and item.offers.listings:
                listing = item.offers.listings[0]
                price_val = float(listing.price.amount) if listing.price else 0.0
                if listing.saving_basis:
                    orig_val = float(listing.saving_basis.amount)

            disc = None
            if orig_val and price_val and orig_val > price_val:
                disc = round((1 - price_val / orig_val) * 100, 1)

            results.append(
                PlatformResult(
                    platform="amazon",
                    product_name=item.item_info.title.display_value if item.item_info and item.item_info.title else query,
                    price=price_val,
                    original_price=orig_val,
                    discount_percent=disc,
                    delivery_time="1-2 days (Prime)",
                    delivery_fee=0.0,
                    product_url=item.detail_page_url or "",
                    product_id=item.asin or "",
                    image_url=(
                        item.images.primary.large.url
                        if item.images and item.images.primary and item.images.primary.large
                        else None
                    ),
                    in_stock=True,
                    rating=None,
                    review_count=None,
                )
            )
        logger.info("amazon_search_ok query=%s results=%d", query, len(results))
        return results

    except Exception as exc:
        logger.error("amazon_search_error query=%s error=%s", query, str(exc)[:200])
        return await _ddg_fallback(query)
