import pytest

from app import create_app
from app.extensions import db
from app.middleware.rate_limiter import reset_rate_limits


@pytest.fixture
def app():
    app = create_app("testing")

    with app.app_context():
        reset_rate_limits()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
        reset_rate_limits()


@pytest.fixture
def client(app):
    return app.test_client()
