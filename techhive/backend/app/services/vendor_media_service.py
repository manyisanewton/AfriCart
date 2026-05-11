from __future__ import annotations

from dataclasses import dataclass

from app.extensions import db
from app.models import Product, ProductImage, Vendor, VendorKYCSubmission
from app.services.storage_service import (
    DOCUMENT_EXTENSIONS,
    IMAGE_EXTENSIONS,
    delete_stored_file,
    save_uploaded_file,
)


@dataclass
class ServiceError:
    details: dict[str, str]
    status_code: int = 400


def add_product_image(
    *,
    vendor: Vendor,
    product_id: int,
    upload,
    alt_text: str | None,
    is_primary: bool,
    sort_order: int,
) -> tuple[ProductImage | None, ServiceError | None]:
    product = Product.query.filter_by(id=product_id, vendor_id=vendor.id).first()
    if product is None:
        return None, ServiceError({"product": "Product not found."}, status_code=404)

    stored, storage_error = save_uploaded_file(
        upload=upload,
        folder=f"products/{product.id}",
        allowed_extensions=IMAGE_EXTENSIONS,
    )
    if storage_error is not None:
        return None, ServiceError({storage_error.field: storage_error.message})

    if is_primary:
        for image in product.images:
            image.is_primary = False
    elif not product.images:
        is_primary = True

    image = ProductImage(
        product_id=product.id,
        image_url=stored["url"],
        alt_text=alt_text,
        is_primary=is_primary,
        sort_order=sort_order,
    )
    db.session.add(image)
    return image, None


def delete_product_image(
    *,
    vendor: Vendor,
    product_id: int,
    image_id: int,
) -> tuple[ProductImage | None, ServiceError | None]:
    product = Product.query.filter_by(id=product_id, vendor_id=vendor.id).first()
    if product is None:
        return None, ServiceError({"product": "Product not found."}, status_code=404)

    image = ProductImage.query.filter_by(id=image_id, product_id=product.id).first()
    if image is None:
        return None, ServiceError({"image": "Image not found."}, status_code=404)

    if image.image_url.startswith("/media/"):
        delete_stored_file(image.image_url.removeprefix("/media/"))

    was_primary = image.is_primary
    db.session.delete(image)
    db.session.flush()

    if was_primary:
        replacement = (
            ProductImage.query.filter_by(product_id=product.id)
            .order_by(ProductImage.sort_order.asc(), ProductImage.id.asc())
            .first()
        )
        if replacement is not None:
            replacement.is_primary = True

    return image, None


def upload_vendor_kyc_document(
    *,
    vendor: Vendor,
    upload,
) -> tuple[dict | None, ServiceError | None]:
    stored, storage_error = save_uploaded_file(
        upload=upload,
        folder=f"vendor-kyc/{vendor.id}",
        allowed_extensions=DOCUMENT_EXTENSIONS,
    )
    if storage_error is not None:
        return None, ServiceError({storage_error.field: storage_error.message})

    submission = vendor.kyc_submission
    previous_url = submission.document_url if submission is not None else None
    if previous_url and previous_url.startswith("/media/"):
        delete_stored_file(previous_url.removeprefix("/media/"))

    return stored, None
