import base64
import json
from datetime import datetime, timezone
from urllib.request import Request, urlopen

from flask import current_app

from app.models import Payment


def _mpesa_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def build_mpesa_password(shortcode: str, passkey: str, timestamp: str) -> str:
    raw = f"{shortcode}{passkey}{timestamp}"
    return base64.b64encode(raw.encode("utf-8")).decode("utf-8")


def normalize_mpesa_phone_number(phone_number: str) -> str:
    value = str(phone_number).strip()
    if value.startswith("+"):
        value = value[1:]
    if value.startswith("0"):
        value = f"254{value[1:]}"
    return value


def classify_mpesa_result_code(result_code: int, result_desc: str | None = None) -> tuple[str, str]:
    classifications = {
        1: ("insufficient_funds", "The M-Pesa account has insufficient funds."),
        1032: ("user_cancelled", "The customer cancelled the payment request."),
        1037: ("request_timeout", "The payment request timed out before completion."),
        2001: ("invalid_phone_number", "The supplied phone number is invalid for M-Pesa."),
        9999: ("provider_error", "M-Pesa returned an unexpected provider error."),
    }
    code, default_message = classifications.get(
        result_code,
        ("provider_declined", "M-Pesa declined or could not complete the payment."),
    )
    return code, result_desc or default_message


def mpesa_is_configured() -> bool:
    required = [
        "MPESA_CONSUMER_KEY",
        "MPESA_CONSUMER_SECRET",
        "MPESA_SHORTCODE",
        "MPESA_PASSKEY",
    ]
    return all(current_app.config.get(key) for key in required)


def get_mpesa_access_token() -> str:
    consumer_key = current_app.config["MPESA_CONSUMER_KEY"]
    consumer_secret = current_app.config["MPESA_CONSUMER_SECRET"]
    token = base64.b64encode(f"{consumer_key}:{consumer_secret}".encode("utf-8")).decode("utf-8")
    request = Request(
        f"{current_app.config['MPESA_BASE_URL']}/oauth/v1/generate?grant_type=client_credentials",
        headers={"Authorization": f"Basic {token}"},
    )
    with urlopen(request, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload["access_token"]


def initiate_mpesa_payment(payment: Payment, callback_base_url: str, phone_number: str) -> dict:
    callback_url = f"{callback_base_url}/mpesa"
    normalized_phone = normalize_mpesa_phone_number(phone_number)

    if not mpesa_is_configured():
        return {
            "provider": "mpesa",
            "checkout_request_id": f"mpesa-checkout-{payment.reference}",
            "merchant_request_id": f"mpesa-merchant-{payment.reference}",
            "phone_number": normalized_phone,
            "callback_url": callback_url,
            "simulated": True,
        }

    timestamp = _mpesa_timestamp()
    access_token = get_mpesa_access_token()
    payload = {
        "BusinessShortCode": current_app.config["MPESA_SHORTCODE"],
        "Password": build_mpesa_password(
            current_app.config["MPESA_SHORTCODE"],
            current_app.config["MPESA_PASSKEY"],
            timestamp,
        ),
        "Timestamp": timestamp,
        "TransactionType": current_app.config["MPESA_TRANSACTION_TYPE"],
        "Amount": int(float(payment.amount)),
        "PartyA": normalized_phone,
        "PartyB": current_app.config["MPESA_SHORTCODE"],
        "PhoneNumber": normalized_phone,
        "CallBackURL": callback_url,
        "AccountReference": f"{current_app.config['MPESA_ACCOUNT_REFERENCE']}-{payment.reference}",
        "TransactionDesc": current_app.config["MPESA_TRANSACTION_DESC"],
    }
    request = Request(
        f"{current_app.config['MPESA_BASE_URL']}/mpesa/stkpush/v1/processrequest",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=15) as response:
        mpesa_response = json.loads(response.read().decode("utf-8"))

    return {
        "provider": "mpesa",
        "checkout_request_id": mpesa_response.get("CheckoutRequestID"),
        "merchant_request_id": mpesa_response.get("MerchantRequestID"),
        "response_code": mpesa_response.get("ResponseCode"),
        "response_description": mpesa_response.get("ResponseDescription"),
        "customer_message": mpesa_response.get("CustomerMessage"),
        "phone_number": normalized_phone,
        "callback_url": callback_url,
    }
