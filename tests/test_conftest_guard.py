"""A pytest that cannot import the app stops with one clear instruction (#146)."""

import importlib.util

import conftest
import pytest


def test_project_venv_has_every_required_module():
    assert conftest.missing_modules() == []


def test_missing_app_stops_the_run_with_venv_instructions(monkeypatch):
    real_find_spec = importlib.util.find_spec
    monkeypatch.setattr(
        importlib.util, 'find_spec',
        lambda name, *args: None if name == 'virtutrade' else real_find_spec(name, *args),
    )
    with pytest.raises(pytest.UsageError) as error:
        conftest.pytest_configure(config=None)
    message = str(error.value)
    assert message.startswith('virtutrade cannot be imported by ')
    assert '.venv/bin/python -m pytest -v' in message
