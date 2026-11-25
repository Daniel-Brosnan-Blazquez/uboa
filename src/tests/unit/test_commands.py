"""Command helpers report subprocess outcomes without running database commands."""
import shlex
import sys

import pytest

from uboa.common.commands import execute_command


@pytest.mark.parametrize("returncode,check_error,success", [(0, True, True), (4, True, False), (4, False, True)])
def test_command_outcomes_and_quoted_arguments(returncode, check_error, success, capsys):
    script = 'import sys; print(sys.argv[1]); print("diagnostic", file=sys.stderr); sys.exit({})'.format(returncode)
    command = shlex.join([sys.executable, "-c", script, "argument with spaces"])
    if success:
        execute_command(command, "Command succeeded", check_error=check_error)
        assert capsys.readouterr().out == "Command succeeded\n"
    else:
        with pytest.raises(SystemExit) as raised:
            execute_command(command, "Command succeeded", check_error=check_error)
        assert raised.value.code == -1
        output = capsys.readouterr().out
        assert "argument with spaces" in output
        assert "diagnostic" in output
        assert "Command succeeded" not in output
