from __future__ import annotations

from decimal import Decimal

from app.blueprints.notifications.schemas import serialize_notification_delivery
from app.blueprints.orders.helpers import serialize_order
from app.blueprints.payments.helpers import serialize_payment
from app.blueprints.support.schemas import serialize_support_ticket
from app.blueprints.vendors.schemas import serialize_vendor_kyc_submission
from app.models import (
    AuditLog,
    NotificationDelivery,
    NotificationDeliveryStatus,
    Order,
    OrderStatus,
    Payment,
    PaymentStatus,
    Product,
    Refund,
    SupportTicket,
    SupportTicketStatus,
    User,
    Vendor,
    VendorKYCStatus,
    VendorKYCSubmission,
    VendorStatus,
)
from app.services.analytics_service import admin_top_products
from app.services.audit_service import serialize_audit_log
from app.services.dashboard_service import build_section, utc_now_iso


RECENT_LIMIT = 5
LOW_STOCK_THRESHOLD = 5


def _money(value) -> str:
    return f"{Decimal(value or 0):.2f}"


def build_admin_dashboard() -> dict:
    total_users = User.query.count()
    active_user_count = User.query.filter_by(is_active=True).count()
    vendor_count = Vendor.query.count()
    approved_vendor_count = Vendor.query.filter_by(status=VendorStatus.APPROVED).count()
    pending_vendor_count = Vendor.query.filter_by(status=VendorStatus.PENDING).count()
    pending_kyc_count = VendorKYCSubmission.query.filter_by(status=VendorKYCStatus.PENDING).count()
    open_support_ticket_count = SupportTicket.query.filter(
        SupportTicket.status.in_([SupportTicketStatus.OPEN, SupportTicketStatus.IN_PROGRESS])
    ).count()
    order_count = Order.query.count()
    pending_order_count = Order.query.filter_by(status=OrderStatus.PENDING).count()
    payment_count = Payment.query.count()
    failed_payment_count = Payment.query.filter_by(status=PaymentStatus.FAILED).count()

    product_count = Product.query.count()
    inactive_product_count = Product.query.filter_by(is_active=False).count()
    low_stock_product_count = Product.query.filter(Product.stock_quantity <= LOW_STOCK_THRESHOLD).count()

    recent_orders = Order.query.order_by(Order.created_at.desc(), Order.id.desc()).limit(RECENT_LIMIT).all()
    recent_payments = Payment.query.order_by(Payment.created_at.desc(), Payment.id.desc()).limit(RECENT_LIMIT).all()
    recent_refunds = Refund.query.order_by(Refund.requested_at.desc(), Refund.id.desc()).limit(RECENT_LIMIT).all()
    recent_support_tickets = (
        SupportTicket.query.order_by(SupportTicket.created_at.desc(), SupportTicket.id.desc())
        .limit(RECENT_LIMIT)
        .all()
    )
    pending_kyc_submissions = (
        VendorKYCSubmission.query.filter_by(status=VendorKYCStatus.PENDING)
        .order_by(VendorKYCSubmission.submitted_at.desc(), VendorKYCSubmission.id.desc())
        .limit(RECENT_LIMIT)
        .all()
    )
    recent_failed_deliveries = (
        NotificationDelivery.query.filter(NotificationDelivery.status == NotificationDeliveryStatus.FAILED)
        .order_by(NotificationDelivery.created_at.desc(), NotificationDelivery.id.desc())
        .limit(RECENT_LIMIT)
        .all()
    )
    latest_audit_events = (
        AuditLog.query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(RECENT_LIMIT).all()
    )

    total_revenue = sum(
        Decimal(payment.amount)
        for payment in Payment.query.filter(Payment.status == PaymentStatus.PAID).all()
    )
    top_products = admin_top_products(limit=RECENT_LIMIT)

    return {
        "persona": "admin",
        "generated_at": utc_now_iso(),
        "summary": {
            "user_count": total_users,
            "active_user_count": active_user_count,
            "vendor_count": vendor_count,
            "approved_vendor_count": approved_vendor_count,
            "pending_vendor_count": pending_vendor_count,
            "pending_kyc_count": pending_kyc_count,
            "open_support_ticket_count": open_support_ticket_count,
            "order_count": order_count,
            "pending_order_count": pending_order_count,
            "payment_count": payment_count,
            "failed_payment_count": failed_payment_count,
            "links": {
                "users": "/api/v1/admin/users",
                "vendors": "/api/v1/admin/vendors",
                "kyc_submissions": "/api/v1/admin/kyc-submissions",
                "support_tickets": "/api/v1/admin/support-tickets",
                "orders": "/api/v1/admin/orders",
                "payments": "/api/v1/payments",
                "notification_deliveries": "/api/v1/admin/notification-deliveries",
            },
        },
        "catalog": build_section(
            links={
                "products": "/api/v1/admin/products",
            },
            items=[
                {
                    **item,
                    "links": {
                        "product_list": "/api/v1/admin/products",
                    },
                }
                for item in top_products
            ],
            total_count=len(top_products),
            limit=RECENT_LIMIT,
            empty_message="No top-product signals yet.",
            product_count=product_count,
            inactive_product_count=inactive_product_count,
            low_stock_product_count=low_stock_product_count,
            top_products=[
                {
                    **item,
                    "links": {
                        "product_list": "/api/v1/admin/products",
                    },
                }
                for item in top_products
            ],
        ),
        "commerce": build_section(
            links={
                "orders": "/api/v1/admin/orders",
                "payments": "/api/v1/payments",
                "refunds": "/api/v1/admin/refunds",
            },
            items=[
                {
                    **serialize_order(order, include_items=True),
                    "links": {"orders": "/api/v1/admin/orders"},
                }
                for order in recent_orders
            ],
            total_count=len(recent_orders),
            limit=RECENT_LIMIT,
            empty_message="No recent commerce activity yet.",
            total_revenue=_money(total_revenue),
            recent_orders=[
                {
                    **serialize_order(order, include_items=True),
                    "links": {"orders": "/api/v1/admin/orders"},
                }
                for order in recent_orders
            ],
            recent_payments=[
                {
                    **serialize_payment(payment),
                    "links": {"payments": "/api/v1/payments"},
                }
                for payment in recent_payments
            ],
            recent_refunds=[
                {
                    "id": refund.id,
                    "order_id": refund.order_id,
                    "amount": refund.amount_value,
                    "reason": refund.reason,
                    "status": refund.status.value,
                    "requested_at": refund.requested_at.isoformat(),
                    "links": {"refunds": "/api/v1/admin/refunds"},
                }
                for refund in recent_refunds
            ],
        ),
        "operations": build_section(
            links={
                "support_tickets": "/api/v1/admin/support-tickets",
                "kyc_submissions": "/api/v1/admin/kyc-submissions",
                "notification_deliveries": "/api/v1/admin/notification-deliveries",
            },
            items=[
                {
                    **serialize_support_ticket(ticket),
                    "links": {"support_tickets": "/api/v1/admin/support-tickets"},
                }
                for ticket in recent_support_tickets
            ],
            total_count=len(recent_support_tickets) + len(pending_kyc_submissions) + len(recent_failed_deliveries),
            limit=RECENT_LIMIT,
            empty_message="No operations alerts right now.",
            recent_support_tickets=[
                {
                    **serialize_support_ticket(ticket),
                    "links": {"support_tickets": "/api/v1/admin/support-tickets"},
                }
                for ticket in recent_support_tickets
            ],
            pending_kyc_submissions=[
                {
                    **serialize_vendor_kyc_submission(submission),
                    "links": {"kyc_submissions": "/api/v1/admin/kyc-submissions"},
                }
                for submission in pending_kyc_submissions
            ],
            failed_notification_deliveries=[
                {
                    **serialize_notification_delivery(delivery),
                    "links": {"notification_deliveries": "/api/v1/admin/notification-deliveries"},
                }
                for delivery in recent_failed_deliveries
            ],
        ),
        "audit": build_section(
            links={
                "audit_logs": "/api/v1/admin/audit-logs",
                "settings": "/api/v1/admin/settings",
                "bulk_notifications": "/api/v1/admin/notifications/bulk",
                "bulk_emails": "/api/v1/admin/emails/bulk",
            },
            items=[
                {
                    **serialize_audit_log(event),
                    "links": {"audit_logs": "/api/v1/admin/audit-logs"},
                }
                for event in latest_audit_events
            ],
            total_count=len(latest_audit_events),
            limit=RECENT_LIMIT,
            empty_message="No recent admin audit events.",
            latest_events=[
                {
                    **serialize_audit_log(event),
                    "links": {"audit_logs": "/api/v1/admin/audit-logs"},
                }
                for event in latest_audit_events
            ],
        ),
    }
