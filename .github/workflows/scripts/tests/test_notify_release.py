"""Tests for notify_release."""
import urllib.error
from unittest.mock import MagicMock, patch

import notify_release
import pytest


def test_build_text_lists_packages():
    text = notify_release.build_text("integrations-core", "abcdef1234567890", '["postgres"]', "http://run")
    assert "pending approval" in text
    assert '["postgres"]' in text
    assert "`abcdef123456`" in text
    assert "http://run" in text


def test_build_text_auto_detect_and_dash_ref():
    text = notify_release.build_text("marketplace", "", "", "http://run")
    assert "auto-detect from tags at HEAD" in text
    assert "ref: `—`" in text


def test_main_no_op_without_url(monkeypatch):
    monkeypatch.delenv("DD_WORKFLOW_WEBHOOK_URL", raising=False)
    with patch.object(notify_release, "post") as post:
        notify_release.main()
    post.assert_not_called()


def test_main_posts_when_configured(monkeypatch):
    monkeypatch.setenv("DD_WORKFLOW_WEBHOOK_URL", "http://webhook")
    with patch.object(notify_release, "post", return_value=True) as post:
        notify_release.main()
    post.assert_called_once()


def test_post_returns_true_on_success():
    with patch("urllib.request.urlopen", return_value=MagicMock()):
        assert notify_release.post("http://webhook", "", "repo", "ref", "", "http://run") is True


def test_post_sends_bearer_token_when_present():
    with patch("urllib.request.urlopen", return_value=MagicMock()) as urlopen:
        notify_release.post("http://webhook", "secret", "repo", "ref", "", "http://run")
    request = urlopen.call_args.args[0]
    assert request.headers["Authorization"] == "Bearer secret"


def test_post_warns_on_transient_network_error(capsys):
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("boom")):
        result = notify_release.post("http://webhook", "", "repo", "ref", "", "http://run")
    assert result is True
    out = capsys.readouterr().out
    assert "transient" in out
    assert "::error::" not in out


@pytest.mark.parametrize("code", [500, 502, 503, 429, 408])
def test_post_warns_on_transient_http_error(code, capsys):
    error = urllib.error.HTTPError("http://webhook", code, "err", {}, None)
    with patch("urllib.request.urlopen", side_effect=error):
        result = notify_release.post("http://webhook", "", "repo", "ref", "", "http://run")
    assert result is True
    out = capsys.readouterr().out
    assert "transient" in out
    assert "::error::" not in out


@pytest.mark.parametrize("code", [400, 401, 403, 404])
def test_post_fails_on_config_http_error(code, capsys, tmp_path, monkeypatch):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    error = urllib.error.HTTPError("http://webhook", code, "err", {}, None)
    with patch("urllib.request.urlopen", side_effect=error):
        result = notify_release.post("http://webhook", "", "repo", "ref", "", "http://run")
    assert result is False
    assert "::error::" in capsys.readouterr().out
    assert f"HTTP {code}" in summary.read_text()


def test_main_exits_nonzero_on_config_error(monkeypatch):
    monkeypatch.setenv("DD_WORKFLOW_WEBHOOK_URL", "http://webhook")
    with patch.object(notify_release, "post", return_value=False):
        with pytest.raises(SystemExit) as excinfo:
            notify_release.main()
    assert excinfo.value.code == 1
