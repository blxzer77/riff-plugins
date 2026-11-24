from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Order:
    order_id: str
    customer_id: str
    total_cents: int
    placed_at: date


@dataclass(frozen=True)
class Customer:
    customer_id: str
    email: str
    lifetime_cents: int
    joined_at: date


@dataclass(frozen=True)
class Refund:
    refund_id: str
    order_id: str
    amount_cents: int
    refunded_at: date


@dataclass(frozen=True)
class Invoice:
    invoice_id: str
    customer_id: str
    amount_cents: int
    issued_at: date
