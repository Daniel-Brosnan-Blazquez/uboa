"""Smoke test an installed UBOA distribution outside its source checkout."""
from importlib.resources import files
from importlib.abc import MetaPathFinder
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

from check_distribution import COMMANDS, RESOURCES, require


class BlockSuiteImports(MetaPathFinder):
    """Verify UBOA runs independently of other BOA suite components."""

    def find_spec(self, fullname, path=None, target=None):
        package = fullname.split(".", 1)[0]
        if package != "uboa" and package.endswith("boa"):
            raise ImportError("UBOA must run independently of other BOA suite components: " + fullname)
        return None


def check():
    package = files("uboa")
    for resource in RESOURCES:
        require(package.joinpath(resource).is_file(), "Missing installed resource: " + resource)
    for command in COMMANDS:
        require(shutil.which(command), "Missing installed command: " + command)

    with TemporaryDirectory(prefix="uboa-installed-") as directory:
        state = Path(directory) / "state"
        state.mkdir()
        for config in package.joinpath("config").iterdir():
            if config.is_file():
                (state / config.name).write_bytes(config.read_bytes())
        log = Path(directory) / "log"
        log.mkdir()
        environment = {
            key: value for key, value in os.environ.items()
            if not key.split("_", 1)[0].endswith("BOA") or key.startswith("UBOA_")
        }
        environment.update({
            "UBOA_LOG_PATH": str(log),
            "UBOA_RESOURCES_PATH": str(state),
        })
        with patch.dict(os.environ, environment, clear=True), patch.object(sys, "meta_path", [BlockSuiteImports(), *sys.meta_path]):
            import uboa.engine.engine
            from uboa.scripts import uboa_init

            with patch.object(uboa_init, "execute_command") as execute, patch.object(uboa_init, "Engine") as engine:
                uboa_init.init(not_insert_users=True)
                engine.assert_not_called()
            execute.assert_called_once()
            arguments = shlex.split(execute.call_args.args[0])
            model = Path(arguments[arguments.index("-f") + 1])
            require(model.samefile(str(package.joinpath("datamodel/uboa_data_model.sql"))), "Initializer did not select bundled SQL")
            for command in ("uboa_init.py",):
                subprocess.run([command, "--help"], check=True, cwd=directory, capture_output=True, text=True)
    print("Validated installed UBOA resources, initializer, imports, and commands")


if __name__ == "__main__":
    check()
