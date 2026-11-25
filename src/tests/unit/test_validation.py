"""Query validation and logging must work without other BOA components."""
import uuid

import pytest

from uboa.engine import functions
from uboa.engine.errors import InputError, UboaLogPathNotAvailable


@pytest.mark.parametrize("validator,value", [
    (functions.is_valid_bool_filter, "true"),
    (functions.is_valid_positive_integer, -1),
    (functions.is_valid_positive_integer, "not a number"),
    (functions.is_valid_order_by, []),
    (functions.is_valid_order_by, {"field": 123, "descending": False}),
    (functions.is_valid_order_by, {"field": "email", "unexpected": False}),
    (functions.is_valid_order_by, {"field": "email", "descending": "false"}),
    (functions.is_valid_text_filter, "email"),
    (functions.is_valid_text_filter, {"filter": "email"}),
    (functions.is_valid_text_filter, {"filter": "email", "op": "unknown"}),
    (functions.is_valid_text_filter, {"filter": 3, "op": "=="}),
    (functions.is_valid_text_filter, {"filter": "email", "op": "in"}),
    (functions.is_valid_text_filter, {"filter": [3], "op": "in"}),
])
def test_malformed_filters_raise_uboa_input_error(validator, value):
    with pytest.raises(InputError):
        validator(value)


@pytest.mark.parametrize("validator,value", [
    (functions.is_valid_bool_filter, False),
    (functions.is_valid_positive_integer, 0),
    (functions.is_valid_positive_integer, "10"),
    (functions.is_valid_order_by, {"field": "email", "descending": False}),
    (functions.is_valid_text_filter, {"filter": "user@example.com", "op": "=="}),
    (functions.is_valid_text_filter, {"filter": [uuid.uuid4()], "op": "in"}),
])
def test_valid_filters_preserve_existing_query_contract(validator, value):
    assert validator(value)


def test_log_directory_cannot_be_a_file(tmp_path, monkeypatch):
    path = tmp_path / "file"
    path.touch()
    monkeypatch.setenv("UBOA_LOG_PATH", str(path))
    with pytest.raises(UboaLogPathNotAvailable):
        functions.get_log_path()
