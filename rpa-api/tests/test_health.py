"""Test health endpoint."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test that health endpoint returns correct response."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_endpoint():
    """Test that root endpoint returns correct response."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"service": "rpa", "status": "ok"}
