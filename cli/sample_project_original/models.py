from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    id: int
    email: str
    name: str
    created_at: datetime
    is_active: bool = True


@dataclass
class Product:
    id: int
    name: str
    price: int
    stock: int
    description: str = ""


@dataclass
class Order:
    id: int
    user_id: int
    product_id: int
    amount: int
    status: str
    created_at: datetime
    paid_at: Optional[datetime] = None


@dataclass
class PaymentRecord:
    id: int
    order_id: int
    method: str
    amount: int
    status: str
    pg_transaction_id: str
    created_at: datetime


ORDER_STATUS = {
    "pending": "결제 대기",
    "paid": "결제 완료",
    "shipped": "배송 중",
    "delivered": "배송 완료",
    "cancelled": "취소됨",
    "refunded": "환불됨",
}

PAYMENT_METHODS = ["card", "transfer", "kakao", "naver", "toss"]
