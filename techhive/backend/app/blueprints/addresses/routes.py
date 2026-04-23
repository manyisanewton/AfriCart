from flask import g, jsonify, request

from app.blueprints.addresses import addresses_bp
from app.blueprints.addresses.schemas import serialize_address, validate_address_payload
from app.blueprints.auth.helpers import validation_error
from app.extensions import db
from app.middleware.auth_required import auth_required
from app.models import Address


def _address_not_found():
    return jsonify({"error": {"code": "not_found", "message": "Address not found."}}), 404


def _address_query():
    return Address.query.filter_by(user_id=g.current_user.id)


def _set_default_address(address: Address) -> None:
    _address_query().update({"is_default": False})
    address.is_default = True


@addresses_bp.get("")
@auth_required
def list_addresses():
    """
    List the authenticated user's addresses.
    ---
    tags:
      - Addresses
    responses:
      200:
        description: User addresses.
    """
    addresses = (
        _address_query()
        .order_by(Address.is_default.desc(), Address.created_at.desc(), Address.id.desc())
        .all()
    )
    return jsonify({"items": [serialize_address(address) for address in addresses]})


@addresses_bp.post("")
@auth_required
def create_address():
    """
    Create a new address for the authenticated user.
    ---
    tags:
      - Addresses
    responses:
      201:
        description: Address created.
    """
    payload = validate_address_payload(request.get_json(silent=True))
    if "errors" in payload:
        return validation_error(payload["errors"])

    address = Address(user_id=g.current_user.id, **payload)
    db.session.add(address)
    db.session.flush()

    existing_count = _address_query().count()
    if payload["is_default"] or existing_count == 1:
        _set_default_address(address)

    db.session.commit()
    return jsonify({"item": serialize_address(address)}), 201


@addresses_bp.patch("/<int:address_id>")
@auth_required
def update_address(address_id: int):
    """
    Update an existing authenticated user's address.
    ---
    tags:
      - Addresses
    responses:
      200:
        description: Address updated.
    """
    address = _address_query().filter_by(id=address_id).first()
    if address is None:
        return _address_not_found()

    payload = validate_address_payload(request.get_json(silent=True))
    if "errors" in payload:
        return validation_error(payload["errors"])

    for field, value in payload.items():
        setattr(address, field, value)

    if payload["is_default"]:
        _set_default_address(address)

    db.session.commit()
    return jsonify({"item": serialize_address(address)})


@addresses_bp.delete("/<int:address_id>")
@auth_required
def delete_address(address_id: int):
    """
    Delete an authenticated user's address.
    ---
    tags:
      - Addresses
    responses:
      200:
        description: Address deleted.
    """
    address = _address_query().filter_by(id=address_id).first()
    if address is None:
        return _address_not_found()

    was_default = address.is_default
    db.session.delete(address)
    db.session.flush()

    if was_default:
        replacement = (
            _address_query()
            .order_by(Address.created_at.desc(), Address.id.desc())
            .first()
        )
        if replacement is not None:
            replacement.is_default = True

    db.session.commit()
    return jsonify({"message": "Address deleted successfully."})


@addresses_bp.post("/<int:address_id>/default")
@auth_required
def set_default_address(address_id: int):
    """
    Mark an address as the authenticated user's default address.
    ---
    tags:
      - Addresses
    responses:
      200:
        description: Default address updated.
    """
    address = _address_query().filter_by(id=address_id).first()
    if address is None:
        return _address_not_found()

    _set_default_address(address)
    db.session.commit()
    return jsonify({"item": serialize_address(address)})
