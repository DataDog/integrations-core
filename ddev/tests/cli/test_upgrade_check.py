# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
import requests
from packaging.version import Version

from ddev.cli.upgrade_check import (
    default_cache_file,
    exit_handler,
    read_last_run,
    upgrade_check,
    write_last_run,
)


@pytest.fixture
def mock_get(mocker):
    return mocker.patch("ddev.cli.upgrade_check.requests.get")


@pytest.fixture
def mock_atexit_register(mocker):
    return mocker.patch("ddev.cli.upgrade_check.atexit.register")


def test_upgrade_reads_valid_cache_file(tmp_path):
    # test ability to read valid cache file
    cache_file = tmp_path / "upgrade_check.json"
    cache_file.write_text('{"version": "1.6.0", "date": "2023-04-11T10:56:39.786412"}')

    last_run = read_last_run(cache_file)
    assert last_run is not None
    version, date = last_run

    assert version == Version("1.6.0")
    assert date == datetime.fromisoformat("2023-04-11T10:56:39.786412")


def test_upgrade_returns_none_when_file_does_not_exist(tmp_path):
    # test ability to return None when file does not exist
    cache_file = tmp_path / "nonexistent.json"

    assert read_last_run(cache_file) is None


def test_upgrade_returns_none_when_data_is_invalid(tmp_path):
    # test ability to return None when file is invalid
    cache_file = tmp_path / "upgrade_check.json"
    cache_file.write_text("not valid json")

    assert read_last_run(cache_file) is None


def test_upgrade_writes_cache_file_and_creates_parent_dirs(tmp_path):
    # test ability to write cache file and create parent directories
    cache_file = tmp_path / "nested" / "dir" / "upgrade_check.json"
    version = Version("1.6.0")
    date = datetime(2023, 4, 11, 10, 56, 39, 786412)

    write_last_run(version, date, cache_file)

    assert cache_file.exists()
    data = json.loads(cache_file.read_text())
    assert data["version"] == "1.6.0"
    assert data["date"] == "2023-04-11T10:56:39.786412"


def test_default_cache_file_uses_platformdirs(monkeypatch):
    import platformdirs

    monkeypatch.setattr(platformdirs, "user_cache_dir", lambda *args, **kwargs: "/tmp/ddev-cache")
    assert default_cache_file().as_posix().endswith("/tmp/ddev-cache/upgrade_check.json")


def test_upgrade_uses_default_cache_file_when_cache_file_is_none(app, mock_get, mocker):
    mock_default_cache_file = mocker.patch("ddev.cli.upgrade_check.default_cache_file")
    mock_read_last_run = mocker.patch(
        "ddev.cli.upgrade_check.read_last_run",
        return_value=(Version("1.0.0"), datetime.now()),
    )

    upgrade_check(app, "1.0.0", cache_file=None)

    mock_default_cache_file.assert_called_once()
    mock_read_last_run.assert_called_once_with(mock_default_cache_file.return_value)
    mock_get.assert_not_called()


def test_upgrade_skips_for_dev_versions(app, tmp_path, mock_get, mock_atexit_register):
    cache_file = tmp_path / "upgrade_check.json"

    upgrade_check(app, "14.1.1.dev91", cache_file=cache_file)

    mock_get.assert_not_called()
    mock_atexit_register.assert_not_called()


def test_upgrade_fetches_from_pypi_and_notifies_when_upgrade_available(app, tmp_path, mock_get, mock_atexit_register):
    # test ability to fetch from PyPI and notify when upgrade is available
    cache_file = tmp_path / "upgrade_check.json"
    mock_response = MagicMock()
    mock_response.json.return_value = {"info": {"version": "2.0.0"}}
    mock_get.return_value = mock_response

    upgrade_check(app, "1.0.0", cache_file=cache_file)

    mock_get.assert_called_once_with("https://pypi.org/pypi/ddev/json", timeout=5)
    mock_atexit_register.assert_called_once_with(exit_handler, app, Version("2.0.0"), Version("1.0.0"))
    # Verify cache was written
    data = json.loads(cache_file.read_text())
    assert data["version"] == "2.0.0"


def test_upgrade_uses_cache_when_fresh(app, tmp_path, mock_get, mock_atexit_register):
    # test ability to use cache when fresh
    cache_file = tmp_path / "upgrade_check.json"
    recent_date = datetime.now() - timedelta(days=1)
    cache_file.write_text(json.dumps({"version": "2.0.0", "date": recent_date.isoformat()}))

    upgrade_check(app, "1.0.0", cache_file=cache_file)

    mock_get.assert_not_called()
    mock_atexit_register.assert_called_once_with(exit_handler, app, Version("2.0.0"), Version("1.0.0"))


def test_upgrade_no_notification_when_up_to_date(app, tmp_path, mock_get, mock_atexit_register):
    # test ability to not notify when up to date
    cache_file = tmp_path / "upgrade_check.json"
    mock_response = MagicMock()
    mock_response.json.return_value = {"info": {"version": "1.0.0"}}
    mock_get.return_value = mock_response

    upgrade_check(app, "1.0.0", cache_file=cache_file)

    mock_atexit_register.assert_not_called()


def test_upgrade_handles_request_exception_gracefully(app, tmp_path, mock_atexit_register, mocker):
    # test ability to handle request exception gracefully
    # and still write to cache to prevent repeated failures
    cache_file = tmp_path / "upgrade_check.json"
    mocker.patch("ddev.cli.upgrade_check.requests.get", side_effect=requests.RequestException("Network error"))

    upgrade_check(app, "1.0.0", cache_file=cache_file)

    mock_atexit_register.assert_not_called()
    # Cache was still written to prevent repeated failures
    assert cache_file.exists()
