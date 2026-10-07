import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings


@pytest.fixture
def client():
    """
    TestClient fixture for making API requests.
    """
    with TestClient(app) as test_client:
        yield test_client
