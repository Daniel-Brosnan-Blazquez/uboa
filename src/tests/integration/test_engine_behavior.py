"""Configuration status handling and update semantics using the real database."""
import json

import pytest

from uboa.datamodel.users import RoleUser, User
from uboa.engine.engine import exit_codes

pytestmark = pytest.mark.integration


def test_custom_configuration_file_is_applied(database, tmp_path):
    path = tmp_path / "custom-users.json"
    data = {"operations": [{"mode": "insert", "users": [
        {"email": "custom@example.com", "username": "custom", "password": "hashed", "roles": ["operator"]}]}]}
    path.write_text(json.dumps(data))
    statuses = database.engine.insert_configuration(str(path))
    assert [item["status"] for item in statuses] == [exit_codes["OK"]["status"]]
    assert [user.username for user in database.query.get_users()] == ["custom"]


def test_missing_configuration_returns_error_without_changing_records(database, records, tmp_path):
    statuses = database.engine.insert_configuration(str(tmp_path / "missing.json"))
    assert [item["status"] for item in statuses] == [exit_codes["FILE_NONEXISTENT"]["status"]]
    assert {user.username for user in database.query.get_users()} == {"alpha", "beta", "gamma"}


def test_schema_validation_can_be_deferred(database, tmp_path):
    path = tmp_path / "unvalidated.json"
    path.write_text("[]")
    result = database.engine.parse_data_from_json(str(path), check_schema=False)
    assert result["status"] == exit_codes["FILE_VALID"]["status"]
    assert database.engine.treat_data() == [exit_codes["DATA_NOT_VALID"]]


def test_unvalidated_unknown_operations_are_skipped(database, records):
    assert database.engine.treat_data({"operations": [{"mode": "unsupported"}]}, validate=False) == []
    assert len(database.query.get_users()) == 3


def test_forced_update_preserves_omitted_account_fields_and_deduplicates_roles(database, records):
    user = records.users[0]
    data = {"operations": [{"mode": "force_insert", "users": [
        {"email": user.email, "username": user.username, "password": "replacement-ignored", "roles": ["operator", "operator"]}]}]}
    assert database.engine.treat_data(data)[0]["status"] == exit_codes["OK"]["status"]
    database.session.expire_all()
    updated = database.session.query(User).filter(User.user_uuid == user.user_uuid).one()
    assert updated.active is True
    assert updated.group == "alpha-team"
    assert updated.password == "hashed"
    assert [role.name for role in updated.roles] == ["operator"]
    assert database.session.query(RoleUser).filter(RoleUser.user_uuid == updated.user_uuid).count() == 1
