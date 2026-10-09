import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./data/test_agenttrace.db"
os.environ["ALLOWED_ORIGINS"] = "http://test"

import pytest
from fastapi.testclient import TestClient
from backend.app.database import Base, engine
from backend.app.main import app


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)
