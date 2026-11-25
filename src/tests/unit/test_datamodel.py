"""Model serialization and role checks operate on unsaved model objects."""
import uuid

import pytest

from uboa.datamodel.errors import WrongParameter
from uboa.datamodel.users import Role, User


@pytest.fixture
def user():
    user = User(uuid.uuid4(), "user@example.com", "user", "team", "hashed", "unique")
    user.roles = [Role(uuid.uuid4(), "operator", "Operations"), Role(uuid.uuid4(), "analyst")]
    return user


def test_user_and_role_serialization(user):
    assert user.jsonify() == {"email": "user@example.com", "username": "user", "password": "hashed",
                              "group": "team", "active": True, "roles": ["operator", "analyst"]}
    assert user.roles[0].jsonify() == {"name": "operator", "description": "Operations"}
    assert user.roles[1].jsonify() == {"name": "analyst", "description": None}


@pytest.mark.parametrize("roles,match", [([], False), (["missing"], False), (["missing", "operator"], True)])
def test_role_membership_and_its_inverse(user, roles, match):
    assert user.has_one_of_these_roles(roles) is match
    assert user.has_none_of_these_roles(roles) is not match


@pytest.mark.parametrize("method", ["has_one_of_these_roles", "has_none_of_these_roles"])
@pytest.mark.parametrize("roles,message", [("operator", "roles parameter must be a list"),
                                         (["missing", 1], "must be a str")])
def test_role_checks_reject_invalid_arguments(user, method, roles, message):
    with pytest.raises(WrongParameter, match=message) as raised:
        getattr(user, method)(roles)
    assert message in raised.value.message
