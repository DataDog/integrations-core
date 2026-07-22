"""Tests for notify_slack."""
import urllib.error
from unittest.mock import patch

import notify_slack


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


def test_post_warns_on_error(capsys):
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("boom")):
        notify_slack.post("token", "C1", "hi")
    assert "failed" in capsys.readouterr().out
