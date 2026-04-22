from __future__ import with_statement

from logging.config import fileConfig
from pathlib import Path

from alembic import context
from flask import current_app


config = context.config

if config.config_file_name is not None:
    config_path = Path(config.config_file_name)
    if not config_path.is_absolute():
        migration_dir = Path(__file__).resolve().parent
        candidates = [
            Path.cwd() / config_path,
            migration_dir / config_path.name,
            migration_dir.parent / config_path,
            migration_dir.parent / config_path.name,
        ]
        for candidate in candidates:
            if candidate.exists():
                config_path = candidate
                break
    if config_path.exists():
        fileConfig(config_path)


target_db = current_app.extensions["migrate"].db
target_metadata = target_db.metadata


def get_engine():
    return target_db.engine


def get_engine_url():
    return str(get_engine().url).replace("%", "%%")


config.set_main_option("sqlalchemy.url", get_engine_url())


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = get_engine()

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
