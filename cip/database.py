from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from cip.settings import get_settings


class Base(DeclarativeBase):
    pass


def engine():
    url = get_settings().database_url
    return create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})


SessionLocal = sessionmaker(bind=engine(), autoflush=False, autocommit=False, expire_on_commit=False)


def init_db() -> None:
    from cip import models  # noqa: F401
    Base.metadata.create_all(engine())


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

