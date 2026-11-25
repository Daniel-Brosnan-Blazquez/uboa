"""User configuration validation rejects malformed input before database work."""
from copy import deepcopy

import pytest

from uboa.engine.errors import ErrorParsingDictionary
from uboa.engine.parsing import validate_data_dictionary


USER = {"email": "user@example.com", "username": "user", "password": "already-hashed"}


@pytest.mark.parametrize("data,message", [
    ({}, "operations key"),
    ({"other": []}, "operations key"),
    ({"operations": [], "extra": []}, "operations key"),
    ({"operations": {}}, "does not contain a list"),
    ({"operations": ["insert"]}, "not corresponding to a dictionary"),
    ({"operations": [{}]}, "does not contain the mode"),
    ({"operations": [{"mode": "delete"}]}, "allowed value"),
    ({"operations": [{"mode": "insert", "extra": 1}]}, "allowed tags"),
    ({"operations": [{"mode": "insert", "users": {}}]}, "users has to be of type list"),
    ({"operations": [{"mode": "insert", "users": ["user"]}]}, "user.*type dict"),
    ({"operations": [{"mode": "insert", "roles": {}}]}, "roles has to be of type list"),
    ({"operations": [{"mode": "insert", "roles": ["operator"]}]}, "role.*type dict"),
    ({"operations": [{"mode": "insert", "roles": [{"unexpected": "operator"}]}]}, "allowed tags"),
    ({"operations": [{"mode": "insert", "roles": [{}]}]}, "name is mandatory"),
    ({"operations": [{"mode": "insert", "roles": [{"name": 1}]}]}, "name.*type string"),
    ({"operations": [{"mode": "insert", "roles": [{"name": "operator", "description": 1}]}]}, "description.*type str"),
])
def test_invalid_operation_structure(data, message):
    with pytest.raises(ErrorParsingDictionary, match=message):
        validate_data_dictionary(data)


@pytest.mark.parametrize("field", ["email", "username", "password"])
@pytest.mark.parametrize("invalid", ["missing", None, 123])
def test_mandatory_identity_fields_are_strings(field, invalid):
    user = deepcopy(USER)
    if invalid == "missing":
        del user[field]
    else:
        user[field] = invalid
    with pytest.raises(ErrorParsingDictionary, match=field):
        validate_data_dictionary({"operations": [{"mode": "insert", "users": [user]}]})


@pytest.mark.parametrize("field,value,message", [
    ("unexpected", 1, "allowed tags"),
    ("active", True, "active.*type str"),
    ("active", "sometimes", "active.*following values"),
    ("roles", "operator", "roles.*type list"),
    ("roles", [1], "roles structure.*type str"),
    ("configurations", "dashboard", "configurations.*type list"),
    ("configurations", [1], "configurations structure.*type str"),
])
def test_optional_user_fields_are_validated(field, value, message):
    with pytest.raises(ErrorParsingDictionary, match=message):
        validate_data_dictionary({"operations": [{"mode": "insert", "users": [dict(USER, **{field: value})]}]})


@pytest.mark.parametrize("mode", ["insert", "erase_and_insert", "force_insert"])
@pytest.mark.parametrize("optional", [{}, {"active": "TRUE", "roles": [], "configurations": []},
    {"active": "false", "roles": ["operator"], "configurations": ["dashboard"]}])
def test_valid_user_and_role_configuration(mode, optional):
    data = {"operations": [{"mode": mode, "users": [dict(USER, **optional)],
                           "roles": [{"name": "operator", "description": "Operations"}]}]}
    original = deepcopy(data)
    validate_data_dictionary(data)
    assert data == original


@pytest.mark.parametrize("data", [
    {"operations": []},
    {"operations": [{"mode": "insert"}]},
    {"operations": [{"mode": "insert", "users": [], "roles": []}]},
    {"operations": [{"mode": "insert", "roles": [{"name": "operator"}]}]},
])
def test_empty_operations_and_optional_sections_are_supported(data):
    validate_data_dictionary(data)
