import logging
from datetime import datetime
from typing import Optional

from flask import request, jsonify, session

from models import Order
from payment import create_order, process_payment, get_order
from utils import generate_order_id

logger = logging.getLogger(__name__)


def get_cart(user_id: int) -> list:
    # TODO: 실제 구현에서는 Redis 또는 DB에서 조회
    return session.get(f"cart_{user_id}", [])


def add_to_cart(user_id: int, product_id: int, quantity: int) -> dict:
    cart = get_cart(user_id)
    for item in cart:
        if item["product_id"] == product_id:
            item["quantity"] += quantity
            session[f"cart_{user_id}"] = cart
            return {"success": True, "cart": cart}

    cart.append({"product_id": product_id, "quantity": quantity})
    session[f"cart_{user_id}"] = cart
    return {"success": True, "cart": cart}


def remove_from_cart(user_id: int, product_id: int) -> dict:
    cart = get_cart(user_id)
    cart = [i for i in cart if i["product_id"] != product_id]
    session[f"cart_{user_id}"] = cart
    return {"success": True, "cart": cart}


def clear_cart(user_id: int) -> None:
    session.pop(f"cart_{user_id}", None)


def validate_cart_items(cart: list) -> tuple[bool, str]:
    if not cart:
        return False, "장바구니가 비어 있습니다"
    for item in cart:
        if item.get("quantity", 0) <= 0:
            return False, f"수량이 유효하지 않습니다: {item}"
    return True, ""


def calculate_cart_total(cart: list, product_prices: dict) -> int:
    total = 0
    for item in cart:
        pid = item["product_id"]
        if pid not in product_prices:
            raise ValueError(f"상품을 찾을 수 없습니다: {pid}")
        total += product_prices[pid] * item["quantity"]
    return total


def apply_coupon(total: int, coupon_code: Optional[str]) -> int:
    if not coupon_code:
        return total
    # TODO: 실제 쿠폰 검증 로직
    MOCK_COUPONS = {"SAVE10": 0.9, "SAVE20": 0.8}
    rate = MOCK_COUPONS.get(coupon_code, 1.0)
    return int(total * rate)


def check_inventory(product_id: int, quantity: int = 1) -> tuple[bool, str]:
    MOCK_STOCK = {1: 100, 2: 50, 3: 0}
    stock = MOCK_STOCK.get(product_id, -1)
    if stock < 0:
        return False, "존재하지 않는 상품입니다"
    if stock == 0:
        return False, "재고가 없습니다"
    if stock < quantity:
        return False, f"재고 부족 (잔여 {stock}개)"
    return True, ""


def checkout(user_id: int, product_id: int, payment_method: str) -> dict:
    if not user_id:
        return {"success": False, "error": "로그인이 필요합니다"}

    product = get_product(product_id)
    amount = product["price"]              # 서버에서 가격 재조회
    if not amount or amount <= 0:
        return {"success": False, "error": "금액이 유효하지 않습니다"}

    order_id = create_order(user_id, product_id, amount)
    result = process_payment(order_id, payment_method)

    if result["success"]:
        logger.info(f"Checkout complete: user={user_id} order={order_id}")
        return {
            "success": True,
            "order_id": order_id,
            "transaction_id": result["transaction_id"],
        }

    logger.warning(f"Checkout failed: {result.get('error')}")
    return result


def get_checkout_status(order_id: str) -> dict:
    order = get_order(order_id)
    if not order:
        return {"found": False}
    return {
        "found": True,
        "status": order["status"],
        "amount": order["amount"],
        "created_at": order["created_at"],
    }
