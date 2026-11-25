"""Exercise every public user/role filter against persisted PostgreSQL records."""
import uuid
from unittest.mock import Mock

import pytest
from sqlalchemy.orm.exc import StaleDataError

from uboa.datamodel.users import Configuration, ConfigurationUser, RoleUser, User
from uboa.engine import query as query_module
from uboa.engine.query import Query

pytestmark = pytest.mark.integration


def text_filter(value, operator):
    return {"op": operator, "filter": [value] if operator == "in" else value}


@pytest.mark.parametrize("operator", ["==", "in"])
@pytest.mark.parametrize("field", ["user_uuids", "emails", "usernames", "groups", "role_uuids", "roles"])
def test_user_filters_find_only_the_matching_identity(database, records, field, operator):
    user, role = records.users[0], records.roles[0]
    values = dict(user_uuids=str(user.user_uuid), emails=user.email, usernames=user.username,
                  groups=user.group, role_uuids=str(role.role_uuid), roles=role.name)
    found = database.query.get_users(**{field: text_filter(values[field], operator)})
    assert [item.user_uuid for item in found] == [user.user_uuid]


@pytest.mark.parametrize("operator", ["==", "in"])
@pytest.mark.parametrize("field", ["role_uuids", "roles", "user_uuids", "emails", "usernames", "groups"])
def test_role_filters_join_only_the_matching_user(database, records, field, operator):
    user, role = records.users[0], records.roles[0]
    values = dict(role_uuids=str(role.role_uuid), roles=role.name, user_uuids=str(user.user_uuid),
                  emails=user.email, usernames=user.username, groups=user.group)
    found = database.query.get_roles(**{field: text_filter(values[field], operator)})
    assert [item.role_uuid for item in found] == [role.role_uuid]


@pytest.mark.parametrize("active,expected", [(True, {"alpha", "gamma"}), (False, {"beta"})])
def test_account_activity_filters_users_and_roles(database, records, active, expected):
    assert {user.username for user in database.query.get_users(active=active)} == expected
    found_roles = {role.name for role in database.query.get_roles(active=active)}
    assert found_roles == {role.name for user, role in zip(records.users, records.roles) if user.username in expected}


@pytest.mark.parametrize("descending", [False, True])
def test_ordering_and_pagination(database, records, descending):
    user_names = sorted([user.username for user in records.users], reverse=descending)
    role_names = sorted([role.name for role in records.roles], reverse=descending)
    order = {"field": "username", "descending": descending}
    assert [user.username for user in database.query.get_users(order_by=order)] == user_names
    assert [user.username for user in database.query.get_users(order_by=order, limit=1, offset=1)] == user_names[1:2]
    order = {"field": "name", "descending": descending}
    assert [role.name for role in database.query.get_roles(order_by=order)] == role_names
    assert [role.name for role in database.query.get_roles(order_by=order, limit=1, offset=1)] == role_names[1:2]


@pytest.mark.parametrize("field", ["configuration_uuids", "configuration_names"])
@pytest.mark.parametrize("operator", ["==", "in"])
def test_configuration_filters_find_associated_users(database, records, field, operator):
    user = records.users[0]
    configuration = Configuration(configuration_uuid=uuid.uuid4(), name="dashboard-alpha", configuration={"theme": "dark"},
                                  permission=1, active=True, user_uuid=user.user_uuid)
    database.session.add(configuration)
    database.session.commit()
    database.session.add(ConfigurationUser(configuration_user_uuid=uuid.uuid4(), user_uuid=user.user_uuid,
                                            configuration_uuid=configuration.configuration_uuid))
    database.session.commit()
    value = str(configuration.configuration_uuid) if field == "configuration_uuids" else configuration.name
    found = database.query.get_users(**{field: text_filter(value, operator)})
    assert [item.user_uuid for item in found] == [user.user_uuid]
    assert database.query.get_users(**{field: text_filter(str(uuid.uuid4()), operator)}) == []
    found = database.query.get_users(roles=text_filter("operator", "=="), **{field: text_filter(value, operator)})
    assert [item.user_uuid for item in found] == [user.user_uuid]


def test_query_can_use_a_callers_session(database, records):
    query = Query(session=database.session)
    try:
        assert query.session is database.session
        assert {user.username for user in query.get_users(delete=None)} == {"alpha", "beta", "gamma"}
    finally:
        query.close_session()


def test_filtered_deletions_commit_and_cascade_role_links(database, records):
    assert database.query.get_users(usernames=text_filter("alpha", "=="), delete=True) == []
    assert {user.username for user in database.query.get_users()} == {"beta", "gamma"}
    assert database.session.query(RoleUser).count() == 2
    assert database.query.get_roles(roles=text_filter("analyst", "=="), delete=True) == []
    assert {role.name for role in database.query.get_roles(delete=None)} == {"operator", "reviewer"}
    assert database.session.query(RoleUser).count() == 1


def test_delete_retries_a_stale_write_before_committing(database, records, monkeypatch):
    statement = database.query.session.query(User).filter(User.username == "alpha")
    original_delete = statement.delete
    attempts = []

    def retrying_delete(**kwargs):
        attempts.append(kwargs)
        if len(attempts) == 1:
            raise StaleDataError("concurrent update")
        return original_delete(**kwargs)

    monkeypatch.setattr(statement, "delete", retrying_delete)
    sleep = Mock()
    monkeypatch.setattr(query_module.time, "sleep", sleep)
    database.query.delete(statement)
    sleep.assert_called_once_with(1)
    assert attempts == [{"synchronize_session": False}] * 2
    assert {user.username for user in database.query.get_users()} == {"beta", "gamma"}
