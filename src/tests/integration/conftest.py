"""Dedicated PostgreSQL fixtures for persistence and query regression tests."""
from types import SimpleNamespace
import uuid

import pytest

from uboa.datamodel.base import Session
from uboa.datamodel.users import Role, RoleUser, User
from uboa.engine.engine import Engine
from uboa.engine.query import Query


@pytest.fixture
def database():
    query = Query()
    query.clear_db()
    engine = Engine(data={"operations": []})
    session = Session()
    try:
        yield SimpleNamespace(query=query, engine=engine, session=session)
    finally:
        session.rollback()
        session.close()
        query.close_session()
        engine.query.close_session()
        engine.close_session()
        query.clear_db()


@pytest.fixture
def records(database):
    users = [User(uuid.uuid4(), name + "@example.com", name, name + "-team", "hashed", str(uuid.uuid4()), active)
             for name, active in [("alpha", True), ("beta", False), ("gamma", True)]]
    roles = [Role(uuid.uuid4(), name) for name in ("operator", "analyst", "reviewer")]
    database.session.add_all(users + roles)
    database.session.commit()
    database.session.add_all([RoleUser(uuid.uuid4(), user.user_uuid, role.role_uuid)
                              for user, role in zip(users, roles)])
    database.session.commit()
    return SimpleNamespace(users=users, roles=roles)
