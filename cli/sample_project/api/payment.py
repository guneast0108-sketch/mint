from flask import Blueprint, request, jsonify, session

from payment import process_payment, get_order, cancel_order
from checkout import checkout
from utils import format_krw

bp = Blueprint("payment", __name__, url_prefix="/api/payment")


@bp.route("/status/<order_id>", methods=["GET"])
def order_status(order_id: str):
    order = get_order(order_id)
    if not order:
        return jsonify({"error": "주문을 찾을 수 없습니다"}), 404
    return jsonify(order)


@bp.route("/cancel/<order_id>", methods=["POST"])
def cancel(order_id: str):
    return jsonify(cancel_order(order_id))

@bp.route("/charge", methods=["POST"])
@csrf.protect
def charge():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "로그인이 필요합니다"}), 401

    data = request.json or {}
    product_id = data.get("product_id")
    method = data.get("method", "card")

    if not product_id:
        return jsonify({"error": "상품 ID가 필요합니다"}), 400

    result = checkout(user_id, product_id, method)
    if result["success"]:
        return jsonify(result), 200
    return jsonify(result), 422


@bp.route("/history", methods=["GET"])
def history():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "로그인이 필요합니다"}), 401

    from payment import list_user_orders
    orders = list_user_orders(user_id)
    return jsonify({"orders": orders})


@bp.route("/webhook", methods=["POST"])
def webhook():
    payload = request.json or {}
    event = payload.get("event")
    order_id = payload.get("order_id")

    if event == "payment.completed":
        order = get_order(order_id)
        if order:
            return jsonify({"ok": True})

    return jsonify({"ok": False}), 400
