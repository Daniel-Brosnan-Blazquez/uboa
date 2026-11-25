"""Check relocated initializer defaults without executing database commands."""
from importlib.resources import files
from pathlib import Path
import runpy
import shlex
from unittest.mock import patch

import pytest

from uboa.scripts import uboa_init as initializer


def test_initializer_uses_bundled_sql_model():
    with patch.object(initializer, "execute_command") as execute, patch.object(initializer, "Engine") as engine:
        initializer.init(not_insert_users=True)
        engine.assert_not_called()
    execute.assert_called_once()
    arguments = shlex.split(execute.call_args.args[0])
    model = Path(arguments[arguments.index("-f") + 1])
    assert model.is_file()
    assert model.samefile(str(files("uboa.datamodel").joinpath("uboa_data_model.sql")))


def test_initializer_rejects_missing_explicit_model(tmp_path, capsys):
    with patch.object(initializer, "execute_command") as execute, pytest.raises(SystemExit) as raised:
        initializer.init(str(tmp_path / "missing.sql"), not_insert_users=True)
    assert raised.value.code == -1
    execute.assert_not_called()
    assert "does not exist" in capsys.readouterr().out


def test_initializer_uses_explicit_model_and_users_file(tmp_path, capsys):
    model = tmp_path / "custom.sql"
    model.write_text("-- custom database model")
    users = str(tmp_path / "users.json")
    with patch.object(initializer, "execute_command") as execute, patch.object(initializer, "Engine") as engine:
        engine.return_value.insert_configuration.return_value = [{"status": 0}, {"status": 10}]
        initializer.init(str(model), users_configuration=users)
        engine.return_value.insert_configuration.assert_called_once_with(users)
    arguments = shlex.split(execute.call_args.args[0])
    assert arguments[arguments.index("-f") + 1] == str(model)
    assert arguments[arguments.index("-h") + 1] == initializer.db_configuration["host"]
    assert arguments[arguments.index("-p") + 1] == str(initializer.db_configuration["port"])
    assert "configuration has been inserted successfully" in capsys.readouterr().out


def test_initializer_reports_all_failed_operations(capsys):
    failures = [{"status": 1, "message": "invalid users"}, {"status": 3, "message": "role conflict"}]
    with patch.object(initializer, "execute_command"), patch.object(initializer, "Engine") as engine:
        engine.return_value.insert_configuration.return_value = [{"status": 0}, *failures]
        with pytest.raises(SystemExit) as raised:
            initializer.init()
    assert raised.value.code == -1
    output = capsys.readouterr().out
    assert "Status: 1, message: invalid users" in output
    assert "Status: 3, message: role conflict" in output


def test_cli_declined_confirmation_does_not_initialize(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["uboa_init.py"])
    monkeypatch.setattr("builtins.input", lambda prompt: "n")
    with patch.object(initializer, "init") as init, pytest.raises(SystemExit) as raised:
        initializer.main()
    assert raised.value.code == 0
    init.assert_not_called()
    assert "aborted" in capsys.readouterr().out


def test_cli_confirmed_reset_uses_default_arguments(monkeypatch):
    monkeypatch.setattr("sys.argv", ["uboa_init.py"])
    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    with patch.object(initializer, "init") as init, pytest.raises(SystemExit) as raised:
        initializer.main()
    assert raised.value.code == 0
    init.assert_called_once_with(None, False, None)


def test_cli_forwards_explicit_paths_and_skip_flag(monkeypatch):
    monkeypatch.setattr("sys.argv", ["uboa_init.py", "-y", "-n", "-f", "model.sql", "-u", "users.json"])
    with patch.object(initializer, "init") as init, patch("builtins.input") as confirm, pytest.raises(SystemExit) as raised:
        initializer.main()
    assert raised.value.code == 0
    confirm.assert_not_called()
    init.assert_called_once_with("model.sql", True, "users.json")


def test_initializer_script_entry_point_can_abort_without_database_work(monkeypatch):
    monkeypatch.setattr("sys.argv", ["uboa_init.py"])
    monkeypatch.setattr("builtins.input", lambda prompt: "n")
    with patch("uboa.common.commands.execute_command") as execute, pytest.raises(SystemExit) as raised:
        runpy.run_path(initializer.__file__, run_name="__main__")
    assert raised.value.code == 0
    execute.assert_not_called()
