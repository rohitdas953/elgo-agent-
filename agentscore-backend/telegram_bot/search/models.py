from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class PlatformResult(BaseModel):
    """A single product result from a platform search."""

    platform: Literal["amazon", "flipkart", "zepto", "instamart"]
    product_name: str
    price: float
    original_price: float | None = None
    discount_percent: float | None = None
    delivery_time: str
    delivery_fee: float = 0.0
    product_url: str
    product_id: str
    image_url: str | None = None
    in_stock: bool = True
    rating: float | None = None
    review_count: int | None = None

    @property
    def total_cost(self) -> float:
        return self.price + self.delivery_fee


class OrderResult(BaseModel):
    """Result from placing an order on a platform."""

    success: bool
    order_id: str | None = None
    estimated_delivery: str | None = None
    tracking_url: str | None = None
    amount_charged: float = 0.0
    error: str | None = None


class PaymentResult(BaseModel):
    """Result from an Algorand payment transaction."""

    success: bool
    txn_id: str | None = None
    amount_algo: float = 0.0
    amount_inr: float = 0.0
    error: str | None = None
