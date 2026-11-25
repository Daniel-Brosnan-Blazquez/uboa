"""Regression coverage for UBOA configuration resource locations."""
from importlib.resources import files
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from uboa.datamodel.functions import (
    config_path,
    get_resources_path,
    UboaResourcesPathNotAvailable,
)


class TestResources(unittest.TestCase):
    def test_default_resource_directory(self):
        with patch.dict(os.environ, {}, clear=True):
            expected = Path(str(files("uboa").joinpath("config")))
            self.assertEqual(Path(get_resources_path()), expected)
            self.assertEqual(Path(config_path("uboa_datamodel.json")), expected / "uboa_datamodel.json")

    def test_component_resource_directory(self):
        from uboa.datamodel.functions import read_configuration
        with TemporaryDirectory() as directory:
            config = {"DDBB_CONFIGURATION": {"host": "uboa-database"}}
            (Path(directory) / "uboa_datamodel.json").write_text(json.dumps(config))
            with patch.dict(os.environ, {"UBOA_RESOURCES_PATH": directory}, clear=True):
                self.assertEqual(get_resources_path(), directory)
                self.assertEqual(read_configuration(), config)
                self.assertEqual(Path(config_path("users.json")), Path(directory) / "users.json")

    def test_missing_resource_directory_is_reported(self):
        with TemporaryDirectory() as directory:
            missing = str(Path(directory) / "missing")
            with patch.dict(os.environ, {"UBOA_RESOURCES_PATH": missing}, clear=True):
                with self.assertRaisesRegex(UboaResourcesPathNotAvailable, "UBOA resources path"):
                    get_resources_path()

    def test_resource_path_must_be_directory(self):
        with TemporaryDirectory() as directory:
            file_path = Path(directory) / "file"
            file_path.touch()
            with patch.dict(os.environ, {"UBOA_RESOURCES_PATH": str(file_path)}, clear=True):
                with self.assertRaises(UboaResourcesPathNotAvailable):
                    get_resources_path()

    def test_missing_component_config_is_reported(self):
        from uboa.datamodel.functions import read_configuration
        with TemporaryDirectory() as component:
            with patch.dict(os.environ, {"UBOA_RESOURCES_PATH": component}, clear=True):
                with self.assertRaises(FileNotFoundError):
                    read_configuration()

    def test_database_host_override_uses_bundled_configuration(self):
        from uboa.datamodel.functions import read_configuration
        with patch.dict(os.environ, {"UBOA_DDBB_HOST": "test-database"}, clear=True):
            self.assertEqual(read_configuration()["DDBB_CONFIGURATION"]["host"], "test-database")

