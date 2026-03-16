"""Tests for _release.dispatch and _release.summary."""
import io
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from _release.dispatch import build_payload, dispatch_in_batches, send_dispatch
from _release.summary import build_summary
from _release import validation as v


class TestSendDispatch:
    _payload = {"event_type": "build-wheels", "client_payload": {}}
    _url = "https://example.com/dispatch"

    def _http_error(self, code: int) -> urllib.error.HTTPError:
        return urllib.error.HTTPError(
            "https://example.com", code, f"HTTP {code}", {}, io.BytesIO(b"error")
        )

    def test_exits_on_4xx(self):
        with patch("urllib.request.urlopen", side_effect=self._http_error(422)), \
             pytest.raises(SystemExit):
            send_dispatch(self._payload, "token", dispatch_url=self._url, max_attempts=1)

    def test_exits_after_5xx_exhausts_retries(self):
        with patch("urllib.request.urlopen", side_effect=self._http_error(500)), \
             pytest.raises(SystemExit):
            send_dispatch(self._payload, "token", dispatch_url=self._url, max_attempts=1)

    def test_succeeds_after_transient_5xx(self):
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value.status = 204
        with patch("_release.dispatch.time.sleep"), \
             patch("urllib.request.urlopen", side_effect=[self._http_error(503), self._http_error(502), mock_ctx]):
            send_dispatch(self._payload, "token", dispatch_url=self._url, max_attempts=3)


class TestBuildPayload:
    def test_structure(self):
        payload = build_payload(["postgres", "mysql"], "integrations-core", "abc123", "prod")
        assert payload["event_type"] == "build-wheels"
        cp = payload["client_payload"]
        assert cp["packages"] == ["postgres", "mysql"]
        assert cp["source_repo"] == "integrations-core"
        assert cp["source_repo_ref"] == "abc123"
        assert cp["target"] == "prod"


class TestDispatchInBatches:
    def test_single_batch(self):
        packages = ["a", "b", "c"]
        with patch("_release.dispatch.send_dispatch") as mock_send:
            dispatch_in_batches(packages, "integrations-core", "sha1", "dev", "tok")
        mock_send.assert_called_once()
        payload = mock_send.call_args[0][0]
        assert payload["client_payload"]["packages"] == packages

    def test_splits_into_batches(self):
        packages = [f"pkg{i}" for i in range(8)]
        with patch("_release.dispatch.send_dispatch") as mock_send:
            dispatch_in_batches(packages, "repo", "ref", "prod", "tok", batch_size=3)
        assert mock_send.call_count == 3
        first_batch = mock_send.call_args_list[0][0][0]["client_payload"]["packages"]
        second_batch = mock_send.call_args_list[1][0][0]["client_payload"]["packages"]
        third_batch = mock_send.call_args_list[2][0][0]["client_payload"]["packages"]
        assert len(first_batch) == 3
        assert len(second_batch) == 3
        assert len(third_batch) == 2

    def test_passes_token(self):
        with patch("_release.dispatch.send_dispatch") as mock_send:
            dispatch_in_batches(["pkg"], "repo", "ref", "dev", "my-token")
        assert mock_send.call_args[0][1] == "my-token"

    def test_empty_packages_does_not_dispatch(self):
        with patch("_release.dispatch.send_dispatch") as mock_send:
            dispatch_in_batches([], "repo", "ref", "dev", "tok")
        mock_send.assert_not_called()

    def test_invalid_batch_size_raises(self):
        with pytest.raises(ValueError):
            dispatch_in_batches(["pkg"], "repo", "ref", "dev", "tok", batch_size=0)


class TestBuildSummary:
    _results = [
        {"package": "postgres", "version": "1.2.3", "type": v.STABLE, "dispatch": True},
        {"package": "mysql", "version": "2.0.0b1", "type": v.PRE_RELEASE, "dispatch": True},
        {"package": "redis", "version": None, "type": v.NO_VERSION, "dispatch": False},
        {"package": "pg", "version": "1.0.0", "type": v.HAS_FRAGMENTS, "dispatch": False},
        {"package": "new_pkg", "version": "0.0.1", "type": v.UNRELEASED, "dispatch": False},
    ]

    def _summary(self, packages=None, **kwargs):
        defaults = dict(
            mode="auto",
            source_repo="integrations-core",
            ref="abc1234567890",
            target="prod",
            dry_run=False,
            dispatched=True,
        )
        return build_summary(packages or ["postgres"], self._results, **{**defaults, **kwargs})

    def test_labels_when_dispatched(self):
        out = build_summary(
            ["postgres", "mysql", "redis", "pg", "new_pkg"],
            self._results,
            mode="auto",
            source_repo="integrations-core",
            ref="sha",
            target="prod",
            dry_run=False,
            dispatched=True,
        )
        assert "✅ Dispatched" in out       # stable and pre-release
        assert "⏭️ Unreleased" in out       # 0.0.1 placeholder
        assert "⚠️ No version" in out
        assert "❌ Unreleased" in out       # has_fragments

    def test_pre_release_dry_run_label(self):
        out = self._summary(packages=["mysql"], dry_run=True, dispatched=False)
        assert "🔄 Dry run" in out

    def test_dry_run_label(self):
        out = self._summary(dry_run=True, dispatched=False)
        assert "🔄 Dry run" in out

    def test_custom_footer(self):
        out = self._summary(dispatched=False, footer="> Custom footer text")
        assert "Custom footer text" in out

    def test_ref_truncated_in_link(self):
        full_sha = "a" * 40
        out = self._summary(ref=full_sha)
        assert full_sha[:12] in out
        assert full_sha[12:] not in out.split("commit/")[0]
