from __future__ import annotations

import asyncio
import logging

from telegram_bot.search import amazon, flipkart, instamart, zepto
from telegram_bot.search.models import PlatformResult

logger = logging.getLogger("agentscore.search.aggregator")

_PLATFORM_TIMEOUT = 12.0  # seconds per platform (DDG searches need more time)


async def _safe_search(
    coro: asyncio.coroutines,  # type: ignore[type-arg]
    platform_name: str,
) -> list[PlatformResult]:
    """Run a platform search with timeout; return [] on any failure."""
    try:
        return await asyncio.wait_for(coro, timeout=_PLATFORM_TIMEOUT)
    except asyncio.TimeoutError:
        logger.warning("search_timeout platform=%s", platform_name)
        return []
    except Exception as exc:
        logger.error(
            "search_error platform=%s error=%s", platform_name, str(exc)[:200]
        )
        return []


async def search_all_platforms(
    search_query: str,
    category: str,
    is_grocery: bool,
) -> list[PlatformResult]:
    """Run all relevant platform searches concurrently and return top 3
    results sorted by total cost (price + delivery_fee)."""

    tasks: list[tuple[str, asyncio.coroutines]] = [  # type: ignore[type-arg]
        ("amazon", amazon.search(search_query)),
        ("flipkart", flipkart.search(search_query)),
    ]

    if is_grocery:
        tasks.append(("zepto", zepto.search(search_query)))
        tasks.append(("instamart", instamart.search(search_query)))

    gathered = await asyncio.gather(
        *(
            _safe_search(coro, name)
            for name, coro in tasks
        ),
        return_exceptions=False,
    )

    all_results: list[PlatformResult] = []
    for batch in gathered:
        if isinstance(batch, list):
            all_results.extend(batch)

    # Filter out-of-stock items
    in_stock = [r for r in all_results if r.in_stock]

    # Sort by total cost ascending
    in_stock.sort(key=lambda r: r.total_cost)

    top = in_stock[:3]
    logger.info(
        "aggregation_complete query=%s total_results=%d returned=%d",
        search_query,
        len(all_results),
        len(top),
    )
    return top
