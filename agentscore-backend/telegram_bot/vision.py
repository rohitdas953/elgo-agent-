from __future__ import annotations

import base64
import json
import logging
import os

import httpx

from telegram_bot.models import ProductInfo

logger = logging.getLogger("agentscore.vision")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

_VISION_PROMPT = (
    "You are a product recognition AI for an Indian e-commerce shopping assistant.\n\n"
    "Analyze this product image and return ONLY a JSON object with no markdown, "
    "no explanation, no preamble:\n"
    "{\n"
    '  "product_name": "string",\n'
    '  "brand": "string or null",\n'
    '  "category": one of ["medicine","grocery","electronics","clothing","beauty","essential","general"],\n'
    '  "search_query": "string optimized for Indian e-commerce search (include brand if visible)",\n'
    '  "is_grocery": boolean\n'
    "}\n\n"
    "If you cannot identify the product clearly, "
    'return: {"product_name": "Unknown Product", "category": "general", '
    '"brand": null, "search_query": "general product", "is_grocery": false}'
)


async def recognize_product(image_bytes: bytes) -> ProductInfo | None:
    """Send image to AI Vision and parse structured product info.

    Priority:
      1. Gemini (Google AI) — if GEMINI_API_KEY is set
      2. Anthropic Claude — if ANTHROPIC_API_KEY is set
      3. Demo fallback — returns Lay's Chips mock data
    """

    if GEMINI_API_KEY:
        result = await _recognize_with_gemini(image_bytes)
        if result:
            return result
        logger.warning("gemini_vision_failed — falling back")

    if ANTHROPIC_API_KEY:
        result = await _recognize_with_anthropic(image_bytes)
        if result:
            return result
        logger.warning("anthropic_vision_failed — falling back")

    # Demo fallback
    logger.warning("No vision API key set — using demo product (Lay's Chips)")
    return ProductInfo(
        product_name="Lay's Potato Chips, Classic (100g)",
        category="grocery",
        brand="Lay's",
        search_query="Lays Classic 100g",
        is_grocery=True,
    )


async def _recognize_with_gemini(image_bytes: bytes) -> ProductInfo | None:
    """Use Google Gemini API for product vision recognition."""
    b64_image = base64.standard_b64encode(image_bytes).decode("ascii")

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": b64_image,
                        }
                    },
                    {"text": _VISION_PROMPT},
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 512,
        },
    }

    try:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        )
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()

        data = resp.json()
        text_block = data["candidates"][0]["content"]["parts"][0]["text"]
        return _parse_vision_response(text_block, "gemini")

    except httpx.HTTPStatusError as exc:
        logger.error(
            "gemini_api_error status=%s body=%s",
            exc.response.status_code,
            exc.response.text[:300],
        )
        return None
    except Exception as exc:
        logger.error("gemini_parse_error error=%s", str(exc)[:200])
        return None


async def _recognize_with_anthropic(image_bytes: bytes) -> ProductInfo | None:
    """Use Anthropic Claude Vision for product recognition."""
    b64_image = base64.standard_b64encode(image_bytes).decode("ascii")

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 512,
        "system": _VISION_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": b64_image,
                        },
                    },
                    {"type": "text", "text": "Identify this product."},
                ],
            }
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()

        data = resp.json()
        text_block = data["content"][0]["text"]
        return _parse_vision_response(text_block, "anthropic")

    except httpx.HTTPStatusError as exc:
        logger.error(
            "anthropic_api_error status=%s body=%s",
            exc.response.status_code,
            exc.response.text[:300],
        )
        return None
    except Exception as exc:
        logger.error("anthropic_parse_error error=%s", str(exc)[:200])
        return None


def _parse_vision_response(raw_text: str, provider: str) -> ProductInfo | None:
    """Parse JSON from AI response text."""
    cleaned = raw_text.strip()
    # Strip markdown fences if model wraps
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned.rsplit("```", 1)[0]
    cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
        product = ProductInfo.model_validate(parsed)
        logger.info(
            "vision_success provider=%s product=%s category=%s",
            provider,
            product.product_name,
            product.category,
        )
        return product
    except (json.JSONDecodeError, KeyError, Exception) as exc:
        logger.error("vision_parse_error provider=%s error=%s", provider, str(exc)[:200])
        return None
