from __future__ import annotations

from pydantic import BaseModel


class ProductInfo(BaseModel):
    """Result from AI vision product recognition."""

    product_name: str
    category: str
    brand: str | None = None
    search_query: str
    is_grocery: bool
