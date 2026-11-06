import pytest
from fastapi.testclient import TestClient

from vera.app import create_app
from vera.config import Settings


@pytest.fixture
def app():
    # Settings() uses plain defaults, so tests never depend on a developer's .env or API key.
    return create_app(Settings())


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client
