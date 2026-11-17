import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Ensure tests run with local fallbacks without waiting for external network retries
os.environ["CIP_MLFLOW_TRACKING_URI"] = ""
os.environ["CIP_QDRANT_URL"] = ""

import cip.models  # noqa: F401
from cip.database import Base
from cip.settings import get_settings

get_settings.cache_clear()


@pytest.fixture()
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

