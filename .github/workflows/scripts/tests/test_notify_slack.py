"""Tests for notify_slack."""
import io
import json
import urllib.error
from contextlib import contextmanager
from unittest.mock import patch

import notify_slack
import pytest


@contextmanager
def fake_slack_response(payload):
    """Patch urlopen to return *payload* as the Slack API JSON body."""
    response = io.BytesIO(json.dumps(payload).encode())
    response.__enter__ = lambda self=response: self
    response.__exit__ = lambda *args: False
    with patch("urllib.request.urlopen", return_value=response):
        yield


def test_build_text_lists_packages():
    text = notify_slack.build_text("integrations-core", "abcdef1234567890", '["postgres"]', "http://run")
    assert "pending approval" in text
    assert '["postgres"]' in text
    assert "`abcdef123456`" in text
    assert "http://run" in text


def test_build_text_auto_detect_and_dash_ref():
    text = notify_slack.build_text("marketplace", "", "", "http://run")
    assert "auto-detect from tags at HEAD" in text
    assert "ref: `—`" in text


def test_main_no_op_without_config(monkeypatch):
    monkeypatch.delenv("SLACK_API_TOKEN", raising=False)
    monkeypatch.setenv("SLACK_CHANNEL_ID", "C1")
    with patch.object(notify_slack, "post") as post:
        notify_slack.main()
    post.assert_not_called()


def test_main_posts_when_configured(monkeypatch):
    monkeypatch.setenv("SLACK_API_TOKEN", "xoxb")
    monkeypatch.setenv("SLACK_CHANNEL_ID", "C1")
    with patch.object(notify_slack, "post") as post:
        notify_slack.main()
    post.assert_called_once()


def test_post_warns_on_transient_network_error(capsys):
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("boom")):
        result = notify_slack.post("token", "C1", "hi")
    assert result is True
    out = capsys.readouterr().out
    assert "transient" in out
    assert "::error::" not in out


def test_post_returns_true_on_success():
    with fake_slack_response({"ok": True}):
        assert notify_slack.post("token", "C1", "hi") is True


def test_post_warns_on_transient_api_error(capsys):
    with fake_slack_response({"ok": False, "error": "rate_limited"}):
        result = notify_slack.post("token", "C1", "hi")
    assert result is True
    out = capsys.readouterr().out
    assert "rate_limited" in out
    assert "::error::" not in out


@pytest.mark.parametrize("error", sorted(notify_slack.CONFIG_ERRORS))
def test_post_fails_on_config_error(error, capsys, tmp_path, monkeypatch):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    with fake_slack_response({"ok": False, "error": error}):
        result = notify_slack.post("token", "C1", "hi")
    assert result is False
    assert "::error::" in capsys.readouterr().out
    assert error in summary.read_text()


def test_main_exits_nonzero_on_config_error(monkeypatch):
    monkeypatch.setenv("SLACK_API_TOKEN", "xoxb")
    monkeypatch.setenv("SLACK_CHANNEL_ID", "C1")
    with patch.object(notify_slack, "post", return_value=False):
        with pytest.raises(SystemExit) as excinfo:
            notify_slack.main()
    assert excinfo.value.code == 1
