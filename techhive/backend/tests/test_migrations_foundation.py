from pathlib import Path

from alembic import command
from sqlalchemy import inspect, text

from app import create_app
from app.extensions import db
from app.services.migration_service import (
    BACKEND_DIR,
    build_alembic_config,
    get_latest_migration_revision,
    get_migration_chain,
    get_migration_heads,
)


def test_migration_chain_has_single_linear_head():
    heads = get_migration_heads()
    chain = get_migration_chain()

    assert len(heads) == 1
    assert heads[0] == get_latest_migration_revision()
    assert chain[0] == "001_initial_tables"
    assert chain[-1] == heads[0]
    assert len(chain) == len(set(chain))


def test_fresh_sqlite_database_upgrades_to_latest_schema(tmp_path):
    database_path = tmp_path / "migration-smoke.db"
    app = create_app("testing")
    app.config.update(
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{database_path}",
        TESTING=True,
    )

    with app.app_context():
        command.upgrade(build_alembic_config(BACKEND_DIR), "head")

        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())
        assert "users" in tables
        assert "payments" in tables
        assert "vendor_kyc_submissions" in tables

        payment_columns = {
            column["name"] for column in inspector.get_columns("payments")
        }
        assert "external_reference" in payment_columns
        assert "failure_code" in payment_columns
        assert "reconciliation_due_at" in payment_columns

        current_revision = db.session.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()
        assert current_revision == get_latest_migration_revision()
