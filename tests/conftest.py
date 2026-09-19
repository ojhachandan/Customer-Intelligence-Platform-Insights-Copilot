import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from cip.database import Base
import cip.models  # noqa: F401


@pytest.fixture()
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

