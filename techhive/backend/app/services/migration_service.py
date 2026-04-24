from __future__ import annotations

from pathlib import Path

from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory


BACKEND_DIR = Path(__file__).resolve().parents[2]


def build_alembic_config(base_dir: Path = BACKEND_DIR) -> AlembicConfig:
    config = AlembicConfig(str(base_dir / "alembic.ini"))
    config.set_main_option("script_location", str(base_dir / "migrations"))
    return config


def get_migration_heads(base_dir: Path = BACKEND_DIR) -> list[str]:
    script = ScriptDirectory.from_config(build_alembic_config(base_dir))
    return list(script.get_heads())


def get_migration_chain(base_dir: Path = BACKEND_DIR) -> list[str]:
    script = ScriptDirectory.from_config(build_alembic_config(base_dir))
    revisions = list(script.walk_revisions(base="base", head="heads"))
    return [revision.revision for revision in reversed(revisions)]


def get_latest_migration_revision(base_dir: Path = BACKEND_DIR) -> str:
    heads = get_migration_heads(base_dir)
    if len(heads) != 1:
        raise RuntimeError(f"Expected a single migration head, found {len(heads)}.")
    return heads[0]
