import hashlib
import hmac
import os
import re
from datetime import datetime


def generate_order_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    rand = os.urandom(4).hex()
    return f"ORD-{timestamp}-{rand.upper()}"


def generate_transaction_id() -> str:
    return os.urandom(16).hex()


def validate_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def mask_card_number(card_number: str) -> str:
    digits = re.sub(r"\D", "", card_number)
    if len(digits) < 8:
        return "****"
    return f"{'*' * (len(digits) - 4)}{digits[-4:]}"


def compute_hmac(secret: str, payload: str) -> str:
    return hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()


def format_krw(amount: int) -> str:
    return f"₩{amount:,}"
