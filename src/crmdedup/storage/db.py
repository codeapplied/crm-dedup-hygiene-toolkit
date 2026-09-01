from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base


def get_engine(db_path: str) -> Engine:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{db_path}")


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    # expire_on_commit=False: the CLI pattern throughout this app queries or
    # commits inside a `with session_factory() as session:` block, then
    # reads the resulting objects' attributes *after* that block exits to
    # build a Rich table — the default expire-on-commit would mark every
    # attribute stale post-commit and try to reload from the now-closed
    # session, raising DetachedInstanceError. Caught by running the CLI
    # end-to-end, not just the test suite (which happened to read
    # attributes while still inside the session in every test).
    return sessionmaker(bind=engine, expire_on_commit=False)
