import shutil

import pytest

from app import create_app
from app.extensions import db
from app.middleware.rate_limiter import reset_rate_limits


@pytest.fixture
def app():
    app = create_app("testing")

    with app.app_context():
        media_root = app.config["STORAGE_LOCAL_ROOT"]
        shutil.rmtree(media_root, ignore_errors=True)
        reset_rate_limits()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
        reset_rate_limits()
        shutil.rmtree(media_root, ignore_errors=True)


@pytest.fixture
def client(app):
    return app.test_client()
