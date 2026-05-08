from __future__ import annotations

from collections import Counter
from decimal import Decimal

from app.models import (
    NotificationDelivery,
    NotificationDeliveryStatus,
    Order,
    OrderStatus,
    Payment,
    PaymentStatus,
    Product,
    Refund,
    RefundStatus,
    SupportTicket,
    SupportTicketStatus,
    User,
    Vendor,
    VendorKYCStatus,
    VendorKYCSubmission,
    VendorStatus,
)
from app.services.analytics_service import admin_summary, vendor_summary


def _money(value) -> str:
    return f"{Decimal(value or 0):.2f}"


def build_admin_overview_report() -> dict:
    summary = admin_summary()
    order_status_breakdown = Counter(order.status.value for order in Order.query.all())
    payment_status_breakdown = Counter(payment.status.value for payment in Payment.query.all())
    vendor_status_breakdown = Counter(vendor.status.value for vendor in Vendor.query.all())
    support_status_breakdown = Counter(ticket.status.value for ticket in SupportTicket.query.all())
    refund_status_breakdown = Counter(refund.status.value for refund in Refund.query.all())

    return {
        "summary": summary,
        "breakdowns": {
            "orders": dict(order_status_breakdown),
            "payments": dict(payment_status_breakdown),
            "vendors": dict(vendor_status_breakdown),
            "support_tickets": dict(support_status_breakdown),
            "refunds": dict(refund_status_breakdown),
        },
    }


def list_vendor_performance(limit: int = 10) -> list[dict]:
    vendors = Vendor.query.order_by(Vendor.created_at.asc(), Vendor.id.asc()).all()
    items = []
    for vendor in vendors:
        summary = vendor_summary(vendor.id)
        items.append(
            {
                "vendor_id": vendor.id,
                "business_name": vendor.business_name,
                "slug": vendor.slug,
                "status": vendor.status.value,
                **summary,
            }
        )
    return sorted(
        items,
        key=lambda item: (
            Decimal(item["revenue"]),
            item["units_sold"],
            item["order_count"],
        ),
        reverse=True,
    )[:limit]


def build_admin_operations_queues() -> dict:
    pending_vendors = Vendor.query.filter_by(status=VendorStatus.PENDING).order_by(Vendor.created_at.asc()).all()
    pending_kyc = (
        VendorKYCSubmission.query.filter_by(status=VendorKYCStatus.PENDING)
        .order_by(VendorKYCSubmission.submitted_at.asc(), VendorKYCSubmission.id.asc())
        .all()
    )
    open_support = (
        SupportTicket.query.filter(
            SupportTicket.status.in_([SupportTicketStatus.OPEN, SupportTicketStatus.IN_PROGRESS])
        )
        .order_by(SupportTicket.created_at.asc(), SupportTicket.id.asc())
        .all()
    )
    pending_refunds = (
        Refund.query.filter_by(status=RefundStatus.REQUESTED)
        .order_by(Refund.requested_at.asc(), Refund.id.asc())
        .all()
    )
    failed_deliveries = (
        NotificationDelivery.query.filter_by(status=NotificationDeliveryStatus.FAILED)
        .order_by(NotificationDelivery.created_at.desc(), NotificationDelivery.id.desc())
        .all()
    )
    stale_pending_payments = (
        Payment.query.filter_by(status=PaymentStatus.PENDING)
        .order_by(Payment.created_at.asc(), Payment.id.asc())
        .all()
    )
    low_stock_products = (
        Product.query.filter(Product.stock_quantity <= 5)
        .order_by(Product.stock_quantity.asc(), Product.id.asc())
        .all()
    )

    return {
        "summary": {
            "pending_vendor_count": len(pending_vendors),
            "pending_kyc_count": len(pending_kyc),
            "open_support_ticket_count": len(open_support),
            "pending_refund_count": len(pending_refunds),
            "failed_notification_delivery_count": len(failed_deliveries),
            "stale_pending_payment_count": len(stale_pending_payments),
            "low_stock_product_count": len(low_stock_products),
        },
        "queues": {
            "pending_vendor_ids": [vendor.id for vendor in pending_vendors[:10]],
            "pending_kyc_submission_ids": [submission.id for submission in pending_kyc[:10]],
            "open_support_ticket_ids": [ticket.id for ticket in open_support[:10]],
            "pending_refund_ids": [refund.id for refund in pending_refunds[:10]],
            "failed_notification_delivery_ids": [delivery.id for delivery in failed_deliveries[:10]],
            "stale_pending_payment_ids": [payment.id for payment in stale_pending_payments[:10]],
            "low_stock_product_ids": [product.id for product in low_stock_products[:10]],
        },
    }
