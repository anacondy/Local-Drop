"""
Shared test fixtures for the Local Drop test suite.

Fully ISOLATED from the real filesystem: HOME and USERPROFILE both point to a
temp dir, so file routing never touches the developer's real folders.
(On Windows, Path.home() reads USERPROFILE, not HOME -- both must be set.)
"""
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture
def app_module(monkeypatch, tmp_path):
    """Isolate filesystem + reset global state; yield the imported module."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    import local_drop
    local_drop.connected_clients.clear()
    local_drop.server_alive = True
    yield local_drop
    local_drop.connected_clients.clear()


@pytest.fixture
def client(app_module):
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


@pytest.fixture
def session_token(app_module):
    return app_module.SESSION_TOKEN


@pytest.fixture
def home(app_module, tmp_path):
    return tmp_path
