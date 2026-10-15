"""Tests for notify_release."""
import http.client
import io
import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

import notify_release

WEBHOOK = "https://api.datadoghq.com/api/v2/workflows/wf-id/instances"


def test_build_text_formats_package_list():
    text = notify_release.build_text(
        "integrations-core", "abcdef1234567890", '["postgres", "mysql"]', "http://run"
    )
    assert text == (
        ":rocket: *Wheel release starting*\n"
        "`integrations-core` · `abcdef123456` · postgres, mysql\n"
        "<http://run|View release run →>"
    )


def test_build_text_auto_detects_packages_and_defaults_ref():
    text = notify_release.build_text("marketplace", "", "", "http://run")
    assert text == (
        ":rocket: *Wheel release starting*\n"
        "`marketplace` · `—` · auto-detect from tags at HEAD\n"
        "<http://run|View release run →>"
    )


def test_build_text_preserves_malformed_package_input():
    text = notify_release.build_text("integrations-core", "abcdef", "postgres, mysql", "http://run")
    assert text == (
        ":rocket: *Wheel release starting*\n"
        "`integrations-core` · `abcdef` · postgres, mysql\n"
        "<http://run|View release run →>"
    )


def test_build_text_escapes_dynamic_slack_text():
    text = notify_release.build_text("core<&>", "<abc", '["postgres<&>"]', "http://run")
    assert text == (
        ":rocket: *Wheel release starting*\n"
        "`core&lt;&amp;&gt;` · `&lt;abc` · postgres&lt;&amp;&gt;\n"
        "<http://run|View release run →>"
    )


@pytest.mark.parametrize("missing", ["DD_API_KEY", "DD_APP_KEY", "DD_WORKFLOW_ID"])
def test_main_fails_without_required_config(missing, monkeypatch, capsys, tmp_path):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setenv("DD_API_KEY", "api")
    monkeypatch.setenv("DD_APP_KEY", "app")
    monkeypatch.setenv("DD_WORKFLOW_ID", "wf-id")
    monkeypatch.delenv(missing)
    with patch.object(notify_release, "post") as post:
        with pytest.raises(SystemExit) as excinfo:
            notify_release.main()
    assert excinfo.value.code == 1
    post.assert_not_called()
    assert "::error::" in capsys.readouterr().out
    assert missing in summary.read_text()


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


@pytest.mark.parametrize(
    "error",
    [urllib.error.URLError("boom"), http.client.RemoteDisconnected("disconnected")],
)
def test_post_warns_on_transient_network_error(error, capsys):
    with patch("urllib.request.urlopen", side_effect=error):
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


def http_error(code, body=b""):
    return urllib.error.HTTPError(WEBHOOK, code, "err", {}, io.BytesIO(body))


@pytest.fixture
def sleep():
    with patch.object(notify_release.time, "sleep") as sleep:
        yield sleep


@pytest.mark.parametrize("code", [400, 404])
def test_post_fails_on_config_http_error(code, capsys, tmp_path, monkeypatch, sleep):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    with patch("urllib.request.urlopen", side_effect=http_error(code, b'{"errors":["bad"]}')) as urlopen:
        result = notify_release.post(WEBHOOK, "api", "app", "hi")
    assert result is False
    assert urlopen.call_count == 1
    sleep.assert_not_called()
    out = capsys.readouterr().out
    assert "::error::" in out
    assert '{"errors":["bad"]}' in out
    assert f"HTTP {code}" in summary.read_text()


@pytest.mark.parametrize("code", [401, 403])
def test_post_retries_auth_error_until_key_propagates(code, capsys, sleep):
    responses = [http_error(code, b"Forbidden"), http_error(code, b"Forbidden"), MagicMock()]
    with patch("urllib.request.urlopen", side_effect=responses) as urlopen:
        result = notify_release.post(WEBHOOK, "api", "app", "hi")
    assert result is True
    assert urlopen.call_count == 3
    assert [c.args[0] for c in sleep.call_args_list] == list(notify_release.AUTH_RETRY_DELAYS[:2])
    out = capsys.readouterr().out
    assert "::error::" not in out
    assert f"HTTP {code}" in out


@pytest.mark.parametrize("code", [401, 403])
def test_post_fails_on_persistent_auth_error(code, capsys, tmp_path, monkeypatch, sleep):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    attempts = len(notify_release.AUTH_RETRY_DELAYS) + 1
    errors = [http_error(code, b'{"errors":["Forbidden"]}') for _ in range(attempts)]
    with patch("urllib.request.urlopen", side_effect=errors) as urlopen:
        result = notify_release.post(WEBHOOK, "api", "app", "hi")
    assert result is False
    assert urlopen.call_count == attempts
    assert sleep.call_count == attempts - 1
    out = capsys.readouterr().out
    assert "::error::" in out
    assert '{"errors":["Forbidden"]}' in out
    assert f"HTTP {code}" in summary.read_text()


def test_main_exits_nonzero_on_config_error(monkeypatch):
    monkeypatch.setenv("DD_API_KEY", "api")
    monkeypatch.setenv("DD_APP_KEY", "app")
    monkeypatch.setenv("DD_WORKFLOW_ID", "wf-id")
    with patch.object(notify_release, "post", return_value=False):
        with pytest.raises(SystemExit) as excinfo:
            notify_release.main()
    assert excinfo.value.code == 1
