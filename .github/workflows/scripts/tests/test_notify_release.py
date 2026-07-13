"""Tests for notify_release."""
import json
import urllib.error
from unittest.mock import MagicMock, patch

import notify_release
import pytest

WEBHOOK = "https://api.datadoghq.com/api/v2/workflows/wf-id/instances"


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


def test_main_no_op_without_credentials(monkeypatch):
    monkeypatch.delenv("DD_API_KEY", raising=False)
    monkeypatch.setenv("DD_APP_KEY", "app")
    monkeypatch.setenv("DD_WORKFLOW_ID", "wf-id")
    with patch.object(notify_release, "post") as post:
        notify_release.main()
    post.assert_not_called()


def test_main_sends_rendered_text(monkeypatch):
    monkeypatch.setenv("DD_API_KEY", "api")
    monkeypatch.setenv("DD_APP_KEY", "app")
    monkeypatch.setenv("DD_WORKFLOW_ID", "wf-id")
    monkeypatch.setenv("SOURCE_REPO", "integrations-core")
    monkeypatch.setenv("REF", "abc123")
    monkeypatch.setenv("PACKAGES", '["postgres"]')
    monkeypatch.setenv("RUN_URL", "http://run")
    with patch.object(notify_release, "post", return_value=True) as post:
        notify_release.main()
    api_url, _, _, text = post.call_args.args
    assert api_url == WEBHOOK
    assert text == notify_release.build_text("integrations-core", "abc123", '["postgres"]', "http://run")


def test_post_wraps_text_and_sets_key_headers():
    with patch("urllib.request.urlopen", return_value=MagicMock()) as urlopen:
        notify_release.post(WEBHOOK, "api", "app", "rendered message")
    request = urlopen.call_args.args[0]
    assert request.headers["Dd-api-key"] == "api"
    assert request.headers["Dd-application-key"] == "app"
    assert json.loads(request.data) == {"meta": {"payload": {"text": "rendered message"}}}


def test_post_returns_true_on_success():
    with patch("urllib.request.urlopen", return_value=MagicMock()):
        assert notify_release.post(WEBHOOK, "api", "app", "hi") is True


def test_post_warns_on_transient_network_error(capsys):
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("boom")):
        result = notify_release.post(WEBHOOK, "api", "app", "hi")
    assert result is True
    out = capsys.readouterr().out
    assert "transient" in out
    assert "::error::" not in out


@pytest.mark.parametrize("code", [500, 502, 503, 429])
def test_post_warns_on_transient_http_error(code, capsys):
    error = urllib.error.HTTPError(WEBHOOK, code, "err", {}, None)
    with patch("urllib.request.urlopen", side_effect=error):
        result = notify_release.post(WEBHOOK, "api", "app", "hi")
    assert result is True
    out = capsys.readouterr().out
    assert "transient" in out
    assert "::error::" not in out


@pytest.mark.parametrize("code", [400, 401, 403, 404])
def test_post_fails_on_config_http_error(code, capsys, tmp_path, monkeypatch):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    error = urllib.error.HTTPError(WEBHOOK, code, "err", {}, None)
    with patch("urllib.request.urlopen", side_effect=error):
        result = notify_release.post(WEBHOOK, "api", "app", "hi")
    assert result is False
    assert "::error::" in capsys.readouterr().out
    assert f"HTTP {code}" in summary.read_text()


def test_main_exits_nonzero_on_config_error(monkeypatch):
    monkeypatch.setenv("DD_API_KEY", "api")
    monkeypatch.setenv("DD_APP_KEY", "app")
    monkeypatch.setenv("DD_WORKFLOW_ID", "wf-id")
    with patch.object(notify_release, "post", return_value=False):
        with pytest.raises(SystemExit) as excinfo:
            notify_release.main()
    assert excinfo.value.code == 1
