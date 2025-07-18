import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, mock_open, MagicMock
from packaging.version import Version

import src.ddev.cli.upgrade_check as uc

class DummyApp:
    def __init__(self):
        self.messages = []
    def display_info(self, msg, highlight=False):
        self.messages.append((msg, highlight))
        return msg

def make_cache(version, date):
    return json.dumps({"version": str(version), "date": date.isoformat()})

@patch("src.ddev.cli.upgrade_check.requests.get")
@patch("src.ddev.cli.upgrade_check.open", new_callable=mock_open)
@patch("src.ddev.cli.upgrade_check.Path.exists", return_value=False)
def test_no_cache_file(mock_exists, mock_open_file, mock_requests):
    app = DummyApp()
    mock_requests.return_value.json.return_value = {"info": {"version": "2.0.0"}}
    mock_requests.return_value.raise_for_status = lambda: None
    uc.upgrade_check(app, "1.0.0")
    assert any("2.0.0" in m[0] for m in app.messages)

@patch("src.ddev.cli.upgrade_check.requests.get")
@patch("src.ddev.cli.upgrade_check.open", new_callable=mock_open)
def test_cache_file_old(mock_open_file, mock_requests):
    app = DummyApp()
    old_date = datetime.now() - timedelta(days=8)
    cache = make_cache("1.5.0", old_date)
    mock_open_file.return_value.__enter__.return_value.read.return_value = cache
    mock_requests.return_value.json.return_value = {"info": {"version": "2.0.0"}}
    mock_requests.return_value.raise_for_status = lambda: None
    with patch("src.ddev.cli.upgrade_check.CACHE_FILE", new=uc.CACHE_FILE):
        uc.upgrade_check(app, "1.0.0")
    assert any("2.0.0" in m[0] for m in app.messages)

@patch("src.ddev.cli.upgrade_check.open", new_callable=mock_open)
def test_cache_file_recent_upgrade_available(mock_open_file):
    app = DummyApp()
    recent_date = datetime.now()
    cache = make_cache("2.0.0", recent_date)
    mock_open_file.return_value.__enter__.return_value.read.return_value = cache
    with patch("src.ddev.cli.upgrade_check.CACHE_FILE", new=uc.CACHE_FILE):
        uc.upgrade_check(app, "1.0.0")
    assert any("2.0.0" in m[0] for m in app.messages)

@patch("src.ddev.cli.upgrade_check.open", new_callable=mock_open)
def test_cache_file_recent_no_upgrade(mock_open_file):
    app = DummyApp()
    recent_date = datetime.now()
    cache = make_cache("1.0.0", recent_date)
    mock_open_file.return_value.__enter__.return_value.read.return_value = cache
    with patch("src.ddev.cli.upgrade_check.CACHE_FILE", new=uc.CACHE_FILE):
        uc.upgrade_check(app, "1.0.0")
    assert not app.messages
