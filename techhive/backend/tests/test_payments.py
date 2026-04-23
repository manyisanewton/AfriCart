from app.extensions import db
from app.blueprints.payments import mpesa as mpesa_module
from app.models import Address, Brand, Category, Product, User, UserRole, Vendor, VendorStatus
from app.blueprints.payments.helpers import sign_webhook_payload
from app.utils.security import hash_password


def auth_headers(client):
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "payment-user@example.com",
            "password": "SecurePass123",
            "first_name": "Payment",
            "last_name": "User",
            "phone_number": "+254755000111",
        },
    )
    token = register_response.get_json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_address_for_registered_user():
    user = User.query.filter_by(email="payment-user@example.com").first()
    address = Address(
        user_id=user.id,
        label="Home",
        recipient_name="Payment User",
        phone_number="+254755000111",
        country="Kenya",
        city="Nairobi",
        state_or_county="Nairobi County",
        postal_code="00100",
        address_line_1="Moi Avenue",
        is_default=True,
    )
    db.session.add(address)
    db.session.commit()
    return address


def create_payment_product():
    vendor_user = User(
        email="vendor-payment@example.com",
        password_hash=hash_password("SecurePass123"),
        first_name="Vendor",
        last_name="Payments",
        phone_number="+254755000222",
        role=UserRole.VENDOR,
    )
    vendor = Vendor(
        user=vendor_user,
        business_name="Payments Tech",
        slug="payments-tech",
        phone_number="+254755000222",
        support_email="support@paymentstech.com",
        status=VendorStatus.APPROVED,
        is_verified=True,
    )
    category = Category(name="Audio", slug="audio")
    brand = Brand(name="JBL", slug="jbl")
    product = Product(
        vendor=vendor,
        category=category,
        brand=brand,
        name="JBL Charge 5",
        slug="jbl-charge-5",
        sku="JBL-CHARGE-5",
        price=18500.00,
        stock_quantity=5,
        is_active=True,
    )
    db.session.add_all([vendor_user, vendor, category, brand, product])
    db.session.commit()
    return product


def create_order_for_payment(client, headers):
    address = create_address_for_registered_user()
    product = create_payment_product()
    cart_response = client.post(
        "/api/v1/cart/items",
        json={"product_id": product.id, "quantity": 1},
        headers=headers,
    )
    assert cart_response.status_code == 201

    order_response = client.post(
        "/api/v1/orders",
        json={"address_id": address.id},
        headers=headers,
    )
    assert order_response.status_code == 201
    return order_response.get_json()["item"]


def test_create_payment_for_order(client):
    headers = auth_headers(client)
    order = create_order_for_payment(client, headers)

    response = client.post(
        "/api/v1/payments",
        json={"order_id": order["id"], "method": "manual"},
        headers=headers,
    )

    assert response.status_code == 201
    item = response.get_json()["item"]
    assert item["order_id"] == order["id"]
    assert item["status"] == "pending"


def test_create_mpesa_payment_requires_phone_number(client):
    headers = auth_headers(client)
    order = create_order_for_payment(client, headers)

    response = client.post(
        "/api/v1/payments",
        json={"order_id": order["id"], "method": "mpesa"},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["details"]["phone_number"] == (
        "phone_number is required for mpesa payments."
    )


def test_create_mpesa_payment_returns_external_reference(client):
    headers = auth_headers(client)
    order = create_order_for_payment(client, headers)

    response = client.post(
        "/api/v1/payments",
        json={"order_id": order["id"], "method": "mpesa", "phone_number": "+254755000111"},
        headers=headers,
    )

    assert response.status_code == 201
    item = response.get_json()["item"]
    assert item["method"] == "mpesa"
    assert item["external_reference"]


def test_list_payments_returns_created_payment(client):
    headers = auth_headers(client)
    order = create_order_for_payment(client, headers)
    client.post(
        "/api/v1/payments",
        json={"order_id": order["id"], "method": "manual"},
        headers=headers,
    )

    response = client.get("/api/v1/payments", headers=headers)

    assert response.status_code == 200
    assert len(response.get_json()["items"]) == 1


def test_mark_payment_paid_updates_order_state(client):
    headers = auth_headers(client)
    order = create_order_for_payment(client, headers)
    payment_response = client.post(
        "/api/v1/payments",
        json={"order_id": order["id"], "method": "manual"},
        headers=headers,
    )
    payment_id = payment_response.get_json()["item"]["id"]

    response = client.post(f"/api/v1/payments/{payment_id}/mark-paid", headers=headers)

    assert response.status_code == 200
    assert response.get_json()["item"]["status"] == "paid"

    order_response = client.get(f"/api/v1/orders/{order['id']}", headers=headers)
    assert order_response.status_code == 200
    assert order_response.get_json()["item"]["status"] == "confirmed"


def test_mark_payment_failed(client):
    headers = auth_headers(client)
    order = create_order_for_payment(client, headers)
    payment_response = client.post(
        "/api/v1/payments",
        json={"order_id": order["id"], "method": "manual"},
        headers=headers,
    )
    payment_id = payment_response.get_json()["item"]["id"]

    response = client.post(f"/api/v1/payments/{payment_id}/mark-failed", headers=headers)

    assert response.status_code == 200
    assert response.get_json()["item"]["status"] == "failed"


def test_signed_webhook_marks_provider_payment_paid(client):
    headers = auth_headers(client)
    order = create_order_for_payment(client, headers)
    payment_response = client.post(
        "/api/v1/payments",
        json={"order_id": order["id"], "method": "mpesa", "phone_number": "+254755000111"},
        headers=headers,
    )
    payment = payment_response.get_json()["item"]
    payload = {
        "reference": payment["reference"],
        "status": "paid",
        "amount": 18500,
        "phone_number": "254755000111",
    }
    import json

    raw_body = json.dumps(payload)
    signature = sign_webhook_payload("mpesa-dev-secret", raw_body)

    response = client.post(
        "/api/v1/payments/webhooks/mpesa",
        data=raw_body,
        content_type="application/json",
        headers={
            "X-TechHive-Signature": signature,
            "X-TechHive-Event-Id": "evt-001",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["item"]["status"] == "paid"


def test_invalid_webhook_signature_is_rejected(client):
    payload = {"reference": "PAY-UNKNOWN", "status": "paid"}
    import json

    response = client.post(
        "/api/v1/payments/webhooks/mpesa",
        data=json.dumps(payload),
        content_type="application/json",
        headers={"X-TechHive-Signature": "invalid"},
    )

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "invalid_signature"


def test_mpesa_client_uses_real_oauth_and_stk_push_when_configured(client, monkeypatch):
    headers = auth_headers(client)
    order = create_order_for_payment(client, headers)

    app = client.application
    app.config["MPESA_CONSUMER_KEY"] = "consumer-key"
    app.config["MPESA_CONSUMER_SECRET"] = "consumer-secret"
    app.config["MPESA_SHORTCODE"] = "174379"
    app.config["MPESA_PASSKEY"] = "pass-key"

    responses = [
        b'{"access_token":"sandbox-token"}',
        b'{"MerchantRequestID":"mreq-123","CheckoutRequestID":"creq-456","ResponseCode":"0","ResponseDescription":"Success","CustomerMessage":"Success"}',
    ]

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def read(self):
            return self.payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(request, timeout=15):
        return FakeResponse(responses.pop(0))

    monkeypatch.setattr(mpesa_module, "urlopen", fake_urlopen)

    response = client.post(
        "/api/v1/payments",
        json={"order_id": order["id"], "method": "mpesa", "phone_number": "0712345678"},
        headers=headers,
    )

    assert response.status_code == 201
    item = response.get_json()["item"]
    assert item["external_reference"] == "creq-456"


def test_mpesa_callback_shape_marks_payment_paid(client):
    headers = auth_headers(client)
    order = create_order_for_payment(client, headers)
    payment_response = client.post(
        "/api/v1/payments",
        json={"order_id": order["id"], "method": "mpesa", "phone_number": "+254755000111"},
        headers=headers,
    )
    payment = payment_response.get_json()["item"]
    payload = {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "merchant-evt-1",
                "CheckoutRequestID": payment["external_reference"],
                "ResultCode": 0,
                "ResultDesc": "The service request is processed successfully.",
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "Amount", "Value": 18500},
                        {"Name": "MpesaReceiptNumber", "Value": "NLJ7RT61SV"},
                        {"Name": "PhoneNumber", "Value": 254755000111},
                    ]
                },
            }
        }
    }
    import json

    raw_body = json.dumps(payload)
    signature = sign_webhook_payload("mpesa-dev-secret", raw_body)

    response = client.post(
        "/api/v1/payments/webhooks/mpesa",
        data=raw_body,
        content_type="application/json",
        headers={"X-TechHive-Signature": signature},
    )

    assert response.status_code == 200
    assert response.get_json()["item"]["status"] == "paid"
    assert response.get_json()["item"]["provider_receipt"] == "NLJ7RT61SV"
    assert response.get_json()["item"]["payer_phone_number"] == "254755000111"


def test_mpesa_callback_rejects_amount_mismatch(client):
    headers = auth_headers(client)
    order = create_order_for_payment(client, headers)
    payment_response = client.post(
        "/api/v1/payments",
        json={"order_id": order["id"], "method": "mpesa", "phone_number": "+254755000111"},
        headers=headers,
    )
    payment = payment_response.get_json()["item"]
    payload = {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "merchant-evt-2",
                "CheckoutRequestID": payment["external_reference"],
                "ResultCode": 0,
                "ResultDesc": "The service request is processed successfully.",
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "Amount", "Value": 100},
                        {"Name": "MpesaReceiptNumber", "Value": "NLJ7RT61SZ"},
                        {"Name": "PhoneNumber", "Value": 254755000111},
                    ]
                },
            }
        }
    }
    import json

    raw_body = json.dumps(payload)
    signature = sign_webhook_payload("mpesa-dev-secret", raw_body)

    response = client.post(
        "/api/v1/payments/webhooks/mpesa",
        data=raw_body,
        content_type="application/json",
        headers={"X-TechHive-Signature": signature},
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "amount_mismatch"


def test_mpesa_callback_duplicate_event_is_idempotent(client):
    headers = auth_headers(client)
    order = create_order_for_payment(client, headers)
    payment_response = client.post(
        "/api/v1/payments",
        json={"order_id": order["id"], "method": "mpesa", "phone_number": "+254755000111"},
        headers=headers,
    )
    payment = payment_response.get_json()["item"]
    payload = {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "merchant-evt-3",
                "CheckoutRequestID": payment["external_reference"],
                "ResultCode": 0,
                "ResultDesc": "The service request is processed successfully.",
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "Amount", "Value": 18500},
                        {"Name": "MpesaReceiptNumber", "Value": "NLJ7RT61SY"},
                        {"Name": "PhoneNumber", "Value": 254755000111},
                    ]
                },
            }
        }
    }
    import json

    raw_body = json.dumps(payload)
    signature = sign_webhook_payload("mpesa-dev-secret", raw_body)

    first = client.post(
        "/api/v1/payments/webhooks/mpesa",
        data=raw_body,
        content_type="application/json",
        headers={"X-TechHive-Signature": signature},
    )
    second = client.post(
        "/api/v1/payments/webhooks/mpesa",
        data=raw_body,
        content_type="application/json",
        headers={"X-TechHive-Signature": signature},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.get_json()["result"] in {"duplicate", "already_processed"}


def test_mpesa_failed_callback_persists_failure_classification(client):
    headers = auth_headers(client)
    order = create_order_for_payment(client, headers)
    payment_response = client.post(
        "/api/v1/payments",
        json={"order_id": order["id"], "method": "mpesa", "phone_number": "+254755000111"},
        headers=headers,
    )
    payment = payment_response.get_json()["item"]
    payload = {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "merchant-evt-4",
                "CheckoutRequestID": payment["external_reference"],
                "ResultCode": 1032,
                "ResultDesc": "Request cancelled by user.",
            }
        }
    }
    import json

    raw_body = json.dumps(payload)
    signature = sign_webhook_payload("mpesa-dev-secret", raw_body)

    response = client.post(
        "/api/v1/payments/webhooks/mpesa",
        data=raw_body,
        content_type="application/json",
        headers={"X-TechHive-Signature": signature},
    )

    assert response.status_code == 200
    item = response.get_json()["item"]
    assert item["status"] == "failed"
    assert item["failure_code"] == "user_cancelled"
    assert item["failure_message"] == "Request cancelled by user."


def test_mpesa_success_callback_requires_complete_metadata(client):
    headers = auth_headers(client)
    order = create_order_for_payment(client, headers)
    payment_response = client.post(
        "/api/v1/payments",
        json={"order_id": order["id"], "method": "mpesa", "phone_number": "+254755000111"},
        headers=headers,
    )
    payment = payment_response.get_json()["item"]
    payload = {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "merchant-evt-5",
                "CheckoutRequestID": payment["external_reference"],
                "ResultCode": 0,
                "ResultDesc": "The service request is processed successfully.",
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "Amount", "Value": 18500},
                        {"Name": "PhoneNumber", "Value": 254755000111},
                    ]
                },
            }
        }
    }
    import json

    raw_body = json.dumps(payload)
    signature = sign_webhook_payload("mpesa-dev-secret", raw_body)

    response = client.post(
        "/api/v1/payments/webhooks/mpesa",
        data=raw_body,
        content_type="application/json",
        headers={"X-TechHive-Signature": signature},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_mpesa_metadata"


def test_mpesa_callback_rejects_duplicate_receipt_for_other_payment(client):
    headers = auth_headers(client)
    first_order = create_order_for_payment(client, headers)
    first_payment_response = client.post(
        "/api/v1/payments",
        json={"order_id": first_order["id"], "method": "mpesa", "phone_number": "+254755000111"},
        headers=headers,
    )
    first_payment = first_payment_response.get_json()["item"]

    second_order = create_order_for_payment(client, headers)
    second_payment_response = client.post(
        "/api/v1/payments",
        json={"order_id": second_order["id"], "method": "mpesa", "phone_number": "+254755000111"},
        headers=headers,
    )
    second_payment = second_payment_response.get_json()["item"]

    import json

    first_payload = {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "merchant-evt-6",
                "CheckoutRequestID": first_payment["external_reference"],
                "ResultCode": 0,
                "ResultDesc": "The service request is processed successfully.",
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "Amount", "Value": 18500},
                        {"Name": "MpesaReceiptNumber", "Value": "NLJ7RT61SA"},
                        {"Name": "PhoneNumber", "Value": 254755000111},
                    ]
                },
            }
        }
    }
    second_payload = {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "merchant-evt-7",
                "CheckoutRequestID": second_payment["external_reference"],
                "ResultCode": 0,
                "ResultDesc": "The service request is processed successfully.",
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "Amount", "Value": 18500},
                        {"Name": "MpesaReceiptNumber", "Value": "NLJ7RT61SA"},
                        {"Name": "PhoneNumber", "Value": 254755000111},
                    ]
                },
            }
        }
    }

    first_response = client.post(
        "/api/v1/payments/webhooks/mpesa",
        data=json.dumps(first_payload),
        content_type="application/json",
        headers={"X-TechHive-Signature": sign_webhook_payload("mpesa-dev-secret", json.dumps(first_payload))},
    )
    second_response = client.post(
        "/api/v1/payments/webhooks/mpesa",
        data=json.dumps(second_payload),
        content_type="application/json",
        headers={"X-TechHive-Signature": sign_webhook_payload("mpesa-dev-secret", json.dumps(second_payload))},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    assert second_response.get_json()["error"]["code"] == "duplicate_receipt"
