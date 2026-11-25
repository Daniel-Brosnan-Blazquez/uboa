# Publishing UBOA

UBOA's distribution name is `uboa`. Package metadata and the release version
live in `pyproject.toml`. Follow these steps to build, install, and publish a
release on PyPI.

## Validate a release locally

Use a virtual environment with a supported Python version (3.9–3.11), such as
the development container. From the repository root:

```bash
python -m pip install build twine
python -m unittest discover -s tools -p 'test_*.py'
python -m build
python -m twine check --strict dist/*
python tools/check_distribution.py dist --tag v1.0.7
```

Use an empty `dist` directory. The tag must match `v` followed by the project
version. Both artifacts include UBOA's runtime resources, commands, MIT license
and authors. Tests remain in the checkout under `src/tests` and are excluded
from both artifacts.

Install each artifact in a clean environment. From outside the checkout, run
the installed-resource checker using its absolute path:

```bash
python -m pip install /path/to/uboa/dist/uboa-1.0.7-py3-none-any.whl
python -m pip check
cd /tmp
python /path/to/uboa/tools/check_installed_resources.py
```

Repeat with the `.tar.gz` source distribution. The checker verifies resources,
commands, imports without other BOA packages and the initializer's bundled SQL
model. It intercepts database initialization commands. The packaging workflow
runs these checks and the database-free tests on Python 3.9 and 3.11. Database
tests run separately in `uboa-testing.yml`.

## Publish a release

1. Update `[project].version` in `pyproject.toml`. Each PyPI release needs a new
   version. Read the installed version with `importlib.metadata.version("uboa")`.
2. Commit and push the release changes. Confirm the packaging and integration
   workflows pass.
3. Configure PyPI Trusted Publishing for this repository's `uboa-publish.yml`
   workflow and the GitHub `pypi` environment before the first upload.
4. Publish a GitHub release whose tag is exactly `v` followed by the package
   version, for example `v1.0.7`, targeting the validated commit.
5. The packaging workflow verifies the tag, builds and checks both artifacts,
   and uploads them to PyPI through the `pypi` environment.
6. Verify [UBOA on PyPI](https://pypi.org/project/uboa/) and install the release
   in a fresh environment with `python -m pip install uboa==1.0.7`.

Pushes and pull requests build and validate artifacts. Only published GitHub
releases upload them. Prereleases also upload: use a PEP 440 version such as
`1.0.8rc1` and the matching `v1.0.8rc1` tag.

## Manual upload

After completing local validation and configuring a PyPI API token locally:

```bash
python -m twine upload dist/*
```
