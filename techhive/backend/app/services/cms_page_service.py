from __future__ import annotations

from datetime import datetime, timezone

from flask import current_app
from sqlalchemy import inspect

from app.extensions import db
from app.models import CmsPage


def _utc_now():
    return datetime.now(timezone.utc)


SYSTEM_CMS_PAGE_DEFINITIONS = [
    {
        "page_key": "return_policy",
        "url": "/return-policy",
        "title": "Return Policy",
        "page_type": "policy",
        "excerpt": "Learn when and how items can be returned on TechHive.",
        "meta_title": "Return Policy | TechHive",
        "meta_description": "Return windows, eligibility, and refund expectations for customer orders on TechHive.",
        "content": """
<h2>Return window</h2>
<p>Most eligible products may be returned within 7 days of delivery when they arrive damaged, defective, incorrect, or materially different from the listing.</p>
<h2>Eligibility</h2>
<ul>
  <li>The item must be in the same condition in which it was received.</li>
  <li>All original accessories, manuals, and packaging should be included where possible.</li>
  <li>Digital goods, custom items, and hygiene-sensitive products may be non-returnable unless faulty.</li>
</ul>
<h2>How returns are handled</h2>
<p>Customers should start a return request from their order history or through support. TechHive may review evidence before approving pickup, drop-off, replacement, or refund.</p>
""".strip(),
    },
    {
        "page_key": "dispute_resolution",
        "url": "/dispute-resolution",
        "title": "Dispute Resolution",
        "page_type": "legal",
        "excerpt": "How customer and seller disputes are reviewed and resolved.",
        "meta_title": "Dispute Resolution | TechHive",
        "meta_description": "Understand how TechHive investigates and resolves order, delivery, and product disputes.",
        "content": """
<h2>Raising a dispute</h2>
<p>If an order issue cannot be solved directly, customers may open a dispute with supporting details such as photos, videos, receipts, or delivery notes.</p>
<h2>Review process</h2>
<p>TechHive reviews the order timeline, seller response, payment confirmation, and shipment evidence before deciding on replacement, refund, rejection, or escalation.</p>
<h2>Resolution outcomes</h2>
<ul>
  <li>Full refund</li>
  <li>Partial refund</li>
  <li>Replacement or resend</li>
  <li>Claim rejection where evidence does not support the report</li>
</ul>
""".strip(),
    },
    {
        "page_key": "advertise_with_us",
        "url": "/advertise-with-us",
        "title": "Advertise With Us",
        "page_type": "marketing",
        "excerpt": "Promotion opportunities for brands and partners on TechHive.",
        "meta_title": "Advertise With Us | TechHive",
        "meta_description": "Reach TechHive shoppers through campaigns, homepage placements, and brand promotions.",
        "content": """
<h2>Promotion opportunities</h2>
<p>Brands and partners can promote through homepage campaigns, featured collections, email placements, seasonal events, and sponsored product slots.</p>
<h2>Who can apply</h2>
<p>Approved vendors, distributors, brand owners, and campaign partners may request marketing support.</p>
<h2>What to include</h2>
<p>When contacting us, include your company name, campaign goal, expected audience, preferred dates, and creative assets if available.</p>
""".strip(),
    },
    {
        "page_key": "report_a_product",
        "url": "/report-a-product",
        "title": "Report a Product",
        "page_type": "help",
        "excerpt": "Report unsafe, counterfeit, misleading, or prohibited products.",
        "meta_title": "Report a Product | TechHive",
        "meta_description": "How customers can flag suspicious or unsafe products listed on TechHive.",
        "content": """
<h2>What should be reported</h2>
<ul>
  <li>Counterfeit or suspicious items</li>
  <li>Unsafe or prohibited products</li>
  <li>Misleading descriptions, photos, or pricing</li>
  <li>Products that infringe intellectual property</li>
</ul>
<h2>How we handle reports</h2>
<p>Our team reviews submitted information, may request additional evidence, and can temporarily restrict, edit, or remove listings while an investigation is underway.</p>
""".strip(),
    },
    {
        "page_key": "payment_information",
        "url": "/payment-information-and-guidelines",
        "title": "Payment Information and Guidelines",
        "page_type": "help",
        "excerpt": "Accepted payment methods, confirmations, and payment safety guidance.",
        "meta_title": "Payment Information and Guidelines | TechHive",
        "meta_description": "Review payment methods, confirmation timing, and safe payment practices on TechHive.",
        "content": """
<h2>Accepted methods</h2>
<p>TechHive may support M-Pesa, card payments, bank transfers, and other methods shown at checkout.</p>
<h2>Payment safety</h2>
<ul>
  <li>Only pay through the official checkout flow.</li>
  <li>Do not send money directly to unverified contacts claiming to represent TechHive.</li>
  <li>Keep payment confirmations until your order is completed.</li>
</ul>
<h2>Verification and timing</h2>
<p>Some payments are confirmed instantly while others may require reconciliation or fraud checks before fulfillment begins.</p>
""".strip(),
    },
    {
        "page_key": "privacy_policy",
        "url": "/privacy-policy",
        "title": "Privacy Policy",
        "page_type": "legal",
        "excerpt": "How TechHive collects, uses, and protects customer data.",
        "meta_title": "Privacy Policy | TechHive",
        "meta_description": "Understand the personal data TechHive collects and how it is processed and protected.",
        "content": """
<h2>Information we collect</h2>
<p>We may collect account details, contact information, order history, support records, device data, and payment-related metadata required to operate the platform.</p>
<h2>How information is used</h2>
<p>Data is used to process orders, manage accounts, prevent fraud, personalize experiences, and communicate service updates.</p>
<h2>Your choices</h2>
<p>Customers may review account details, manage notification preferences, and request assistance regarding personal data where applicable.</p>
""".strip(),
    },
    {
        "page_key": "shipping_delivery_policy",
        "url": "/shipping-and-delivery-policy",
        "title": "Shipping and Delivery Policy",
        "page_type": "policy",
        "excerpt": "Delivery timelines, zones, costs, and customer expectations.",
        "meta_title": "Shipping and Delivery Policy | TechHive",
        "meta_description": "Learn how delivery zones, fulfillment timelines, and shipping charges work on TechHive.",
        "content": """
<h2>Delivery coverage</h2>
<p>Shipping availability depends on the customer address, vendor fulfillment capability, and active delivery zones configured on the platform.</p>
<h2>Estimated timelines</h2>
<p>Delivery times vary by location, stock availability, courier capacity, and payment confirmation. Estimates shown during checkout are not guaranteed unless stated otherwise.</p>
<h2>Shipping charges</h2>
<p>Shipping fees may be calculated by location, order value, vendor rules, or promotional campaigns.</p>
""".strip(),
    },
    {
        "page_key": "warranty_policy",
        "url": "/warranty-policy",
        "title": "Warranty Policy",
        "page_type": "policy",
        "excerpt": "Warranty coverage expectations for eligible products.",
        "meta_title": "Warranty Policy | TechHive",
        "meta_description": "Review warranty support, exclusions, and claim expectations for products sold on TechHive.",
        "content": """
<h2>Warranty coverage</h2>
<p>Warranty terms may differ by product, brand, and seller. Any stated manufacturer or seller warranty should be referenced on the product detail page or invoice.</p>
<h2>Exclusions</h2>
<ul>
  <li>Physical misuse or accidental damage</li>
  <li>Unauthorized repairs or modifications</li>
  <li>Normal wear and tear</li>
</ul>
<h2>Claims</h2>
<p>Customers should submit the order reference, issue description, and supporting evidence when starting a warranty claim.</p>
""".strip(),
    },
    {
        "page_key": "order_cancellation_policy",
        "url": "/order-cancellation-policy",
        "title": "Order Cancellation Policy",
        "page_type": "policy",
        "excerpt": "When customers or TechHive may cancel orders and what happens next.",
        "meta_title": "Order Cancellation Policy | TechHive",
        "meta_description": "Learn when orders can be cancelled and how refunds are handled after cancellation.",
        "content": """
<h2>Customer cancellations</h2>
<p>Orders may be cancelled before processing or shipment begins, subject to seller rules and payment status.</p>
<h2>Platform or seller cancellations</h2>
<p>Orders may be cancelled due to stock issues, pricing errors, fraud concerns, failed delivery coordination, or compliance reviews.</p>
<h2>Refund timing</h2>
<p>Where payment has already been captured, eligible cancellations are followed by a refund based on the original payment method and reconciliation timeline.</p>
""".strip(),
    },
    {
        "page_key": "buyer_protection_policy",
        "url": "/buyer-protection-policy",
        "title": "Buyer Protection Policy",
        "page_type": "policy",
        "excerpt": "Customer safeguards for qualifying orders and disputes.",
        "meta_title": "Buyer Protection Policy | TechHive",
        "meta_description": "Understand the protections available to customers when orders go wrong on TechHive.",
        "content": """
<h2>What buyer protection covers</h2>
<ul>
  <li>Items not delivered</li>
  <li>Items that arrive damaged or defective</li>
  <li>Items materially different from the listing</li>
</ul>
<h2>Conditions</h2>
<p>Claims must be submitted within the stated review window and include enough evidence for investigation.</p>
<h2>Resolution</h2>
<p>Depending on findings, TechHive may issue refunds, arrange replacements, or require additional verification before a final decision is made.</p>
""".strip(),
    },
]


def ensure_system_cms_pages() -> None:
    inspector = inspect(db.engine)
    if not inspector.has_table("cms_pages"):
        current_app.logger.info("Skipping system CMS page setup because cms_pages table does not exist yet.")
        return

    created = 0
    updated = 0

    for definition in SYSTEM_CMS_PAGE_DEFINITIONS:
        page = CmsPage.query.filter_by(page_key=definition["page_key"]).first()
        if page is None:
            page = CmsPage(
                page_key=definition["page_key"],
                url=definition["url"],
                title=definition["title"],
                page_type=definition["page_type"],
                status="published",
                excerpt=definition["excerpt"],
                content=definition["content"],
                meta_title=definition["meta_title"],
                meta_description=definition["meta_description"],
                registration_required=False,
                is_system_page=True,
                allow_indexing=True,
                published_at=_utc_now(),
            )
            db.session.add(page)
            created += 1
            continue

        changed = False
        immutable_defaults = {
            "url": definition["url"],
            "title": definition["title"],
            "page_type": definition["page_type"],
        }
        for field, value in immutable_defaults.items():
            if not getattr(page, field):
                setattr(page, field, value)
                changed = True

        if not page.excerpt:
            page.excerpt = definition["excerpt"]
            changed = True
        if not page.content:
            page.content = definition["content"]
            changed = True
        if not page.meta_title:
            page.meta_title = definition["meta_title"]
            changed = True
        if not page.meta_description:
            page.meta_description = definition["meta_description"]
            changed = True
        if not page.status:
            page.status = "published"
            changed = True
        if page.published_at is None and page.status == "published":
            page.published_at = _utc_now()
            changed = True
        if not page.is_system_page:
            page.is_system_page = True
            changed = True

        if changed:
            updated += 1

    if created or updated:
        db.session.commit()
        current_app.logger.info("System CMS pages ensured: %s created, %s updated.", created, updated)
