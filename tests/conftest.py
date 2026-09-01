import pytest

from crmdedup.storage.db import get_engine, get_session_factory, init_db


@pytest.fixture
def db_session(tmp_path):
    """An initialized DB session against a throwaway temp DB — isolates
    every test from the real data/ directory and from each other."""
    engine = get_engine(str(tmp_path / "test.db"))
    init_db(engine)
    session_factory = get_session_factory(engine)
    with session_factory() as session:
        yield session
