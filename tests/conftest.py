"""Stop the run early when this pytest cannot import the app (#146).

A pytest outside the project venv, such as the global pipx copy in GitHub
Codespaces, cannot see virtutrade or Flask and would otherwise report one
ModuleNotFoundError per test module.
"""

import importlib.util
import sys

import pytest

REQUIRED_MODULES = ('virtutrade', 'flask')


def missing_modules(names=REQUIRED_MODULES):
    return [name for name in names if importlib.util.find_spec(name) is None]


def pytest_configure(config):
    missing = missing_modules()
    if missing:
        raise pytest.UsageError(
            f"{', '.join(missing)} cannot be imported by {sys.executable}.\n"
            'This pytest is not running in the project venv. From the repository root run:\n'
            '  .venv/bin/python -m pip install -e ".[dev]"\n'
            '  .venv/bin/python -m pytest -v\n'
            'On Windows use .\\.venv\\Scripts\\python.exe instead of .venv/bin/python. '
            'See docs/SETUP.md#tests.'
        )
