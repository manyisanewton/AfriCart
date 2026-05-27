from datetime import datetime, timezone

from app.extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


partner_users = db.Table(
    "partner_users",
    db.Column("partner_id", db.Integer, db.ForeignKey("partners.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
)


class Partner(db.Model):
    __tablename__ = "partners"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False, unique=True)
    code = db.Column(db.String(80), nullable=True, unique=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    users = db.relationship(
        "User",
        secondary=partner_users,
        back_populates="partners",
        lazy="selectin",
    )
    suppliers = db.relationship(
        "Supplier",
        back_populates="partner",
        lazy="selectin",
    )
