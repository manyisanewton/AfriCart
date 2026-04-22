from app.tasks import (
    build_cleanup_summary,
    build_daily_sales_report,
    build_image_job_payload,
    send_order_confirmation_email,
    send_payment_status_sms,
)


def test_worker_health_endpoint(client):
    response = client.get("/workers/health")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "available"
    assert payload["task_queue"]["broker_url"] == "redis://redis:6379/0"


def test_root_exposes_worker_health_url(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.get_json()["worker_health_url"] == "/workers/health"


def test_async_task_helpers_return_expected_payloads(app):
    with app.app_context():
        email_payload = send_order_confirmation_email(
            to_email="buyer@example.com",
            order_number="TH-001",
            total_amount="1500.00",
        )
        sms_payload = send_payment_status_sms(
            phone_number="+254700000001",
            order_number="TH-001",
            status="paid",
        )

    report_payload = build_daily_sales_report(total_orders=8, gross_sales="45000.00")
    cleanup_payload = build_cleanup_summary(cleaned_items=3, task_name="cleanup.notifications")
    image_payload = build_image_job_payload(
        image_url="https://example.com/image.jpg",
        transforms=["thumbnail", "webp"],
    )

    assert email_payload["channel"] == "email"
    assert email_payload["template"] == "order_confirmation"
    assert sms_payload["channel"] == "sms"
    assert "TH-001" in sms_payload["message"]
    assert report_payload["total_orders"] == 8
    assert cleanup_payload["task_name"] == "cleanup.notifications"
    assert image_payload["transforms"] == ["thumbnail", "webp"]
