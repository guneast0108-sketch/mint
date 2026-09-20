import sqlite3
import logging
from datetime import datetime
from typing import Optional

from models import PaymentRecord, Order
from utils import generate_transaction_id, generate_order_id, format_krw

logger = logging.getLogger(__name__)

DB_PATH = "payment.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            is_active INTEGER DEFAULT 1
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            paid_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS payment_records (
            id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            method TEXT NOT NULL,
            amount INTEGER NOT NULL,
            status TEXT NOT NULL,
            pg_transaction_id TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def create_order(user_id: int, product_id: int, amount: int) -> str:
    order_id = generate_order_id()
    conn = get_connection()
    conn.execute(
        "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)",
        (order_id, user_id, product_id, amount, "pending",
         datetime.now().isoformat(), None),
    )
    conn.commit()
    conn.close()
    logger.info(f"Order created: {order_id}")
    return order_id


def get_order(order_id: str) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def list_user_orders(user_id: int) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def process_payment(order_id: str, method: str) -> dict:
    order = get_order(order_id)
    if not order:
        return {"success": False, "error": "주문을 찾을 수 없습니다"}

    if order["status"] != "pending":
        return {"success": False, "error": "이미 처리된 주문입니다"}

    tx_id = generate_transaction_id()

    conn = get_connection()
    conn.execute(
        "UPDATE orders SET status = 'paid', paid_at = ? WHERE id = ?",
        (datetime.now().isoformat(), order_id),
    )
    conn.execute(
        "INSERT INTO payment_records VALUES (?, ?, ?, ?, ?, ?, ?)",
        (generate_transaction_id(), order_id, method,
         order["amount"], "success", tx_id, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()

    logger.info(f"Payment processed: {order_id} via {method}")
    return {"success": True, "transaction_id": tx_id}


def get_payment_history(order_id: str) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM payment_records WHERE order_id = ? ORDER BY created_at DESC",
        (order_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_user_payment_summary(user_id: int) -> dict:
    orders = list_user_orders(user_id)
    paid = [o for o in orders if o["status"] == "paid"]
    total = sum(o["amount"] for o in paid)
    return {
        "total_orders": len(orders),
        "paid_orders": len(paid),
        "total_amount": total,
    }


def get_user_by_id(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_payment_stats() -> dict:
    conn = get_connection()
    total = conn.execute(
        "SELECT COUNT(*), SUM(amount) FROM payment_records WHERE status = 'success'"
    ).fetchone()
    conn.close()
    return {"count": total[0] or 0, "total_amount": total[1] or 0}


def cancel_order(order_id: str) -> dict:
    order = get_order(order_id)
    if not order:
        return {"success": False, "error": "주문을 찾을 수 없습니다"}

    if order["status"] not in ("pending", "paid"):
        return {"success": False, "error": "취소할 수 없는 주문 상태입니다"}

    conn = get_connection()
    conn.execute(
        "UPDATE orders SET status = 'cancelled' WHERE id = ?", (order_id,)
    )
    conn.commit()
    conn.close()
    logger.info(f"Order cancelled: {order_id}")
    return {"success": True}


def calculate_total(user_id: int) -> int:
    orders = list_user_orders(user_id)
    return sum(o["amount"] for o in orders if o["status"] == "paid")
