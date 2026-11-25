"""
Functions definition for the datamodel component

Written by Daniel Brosnan Blázquez

module uboa
"""
# Import python utilities
from importlib.resources import files
import os
import json
from pathlib import Path


class UboaResourcesPathNotAvailable(FileNotFoundError):
    """The configured UBOA resource directory is unavailable."""


def get_resources_path():
    """Return UBOA_RESOURCES_PATH, defaulting to the bundled config directory."""
    directory = os.environ.get("UBOA_RESOURCES_PATH", str(files("uboa").joinpath("config")))
    if not os.path.isdir(directory):
        raise UboaResourcesPathNotAvailable("The UBOA resources path {} is not available".format(directory))
    return directory


def config_path(filename):
    return str(Path(get_resources_path()) / filename)


def read_configuration():
    # Get configuration
    with open(config_path("uboa_datamodel.json")) as json_data_file:
        config = json.load(json_data_file)
    # end with

    if "UBOA_DDBB_HOST" in os.environ:
        config["DDBB_CONFIGURATION"]["host"] = os.environ["UBOA_DDBB_HOST"]
    # end if

    return config
