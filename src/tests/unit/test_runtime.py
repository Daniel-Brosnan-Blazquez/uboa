"""Logging, profiling and query diagnostics must tolerate their failure paths."""
import logging
from unittest.mock import Mock

import pytest

from uboa import debugging
from uboa.engine import query
from uboa.engine.errors import EmailNotCorrect, UsernameNotCorrect
from uboa.logging import Log, RotatingFileHandlerAllUsers


@pytest.mark.parametrize("level", [logging.DEBUG, logging.INFO])
def test_profiling_preserves_function_contract(monkeypatch, level):
    logger = Mock(level=level)
    monkeypatch.setattr(debugging, "logger", logger)

    @debugging.debug
    def add(first, second=0):
        """Add values without changing the signature of the decorated call."""
        return first + second

    assert add(2, second=3) == 5
    assert add.__name__ == "add"
    assert "Add values" in add.__doc__
    assert logger.debug.call_count == (2 if level == logging.DEBUG else 1)
    if level == logging.DEBUG:
        assert "lasted" in logger.debug.call_args.args[0]


def test_default_logger_reconfiguration_does_not_duplicate_handlers(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("UBOA_LOG_PATH", str(tmp_path))
    monkeypatch.setenv("UBOA_STREAM_LOG", "1")
    wrapper = Log()
    logger = wrapper.logger
    try:
        wrapper.define_logging_configuration()
        assert sum(type(h) is logging.StreamHandler for h in logger.handlers) == 1
        assert sum(isinstance(h, RotatingFileHandlerAllUsers) for h in logger.handlers) == 1
        monkeypatch.delenv("UBOA_STREAM_LOG")
        wrapper.define_logging_configuration()
        assert not any(type(h) is logging.StreamHandler for h in logger.handlers)
        logger.setLevel(logging.CRITICAL)
        logger.debugi("disabled custom message")
        assert "disabled custom message" not in capsys.readouterr().err
    finally:
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)


def test_unprintable_query_does_not_prevent_execution(monkeypatch):
    logger = Mock()
    monkeypatch.setattr(query, "logger", logger)

    def unprintable(statement):
        raise NotImplementedError("unsupported literal")

    monkeypatch.setattr(query, "literal_query", unprintable)
    query.log_query(Mock())
    assert "unsupported literal" in logger.debug.call_args.args[0]


@pytest.mark.parametrize("error", [EmailNotCorrect, UsernameNotCorrect])
def test_identity_errors_preserve_diagnostics(error):
    problem = error("invalid identity")
    assert problem.message == "invalid identity"
    assert str(problem) == "invalid identity"
