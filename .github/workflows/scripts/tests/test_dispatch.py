"""Tests for _release.dispatch and _release.summary."""
from unittest.mock import patch

from _release.dispatch import BATCH_SIZE, build_payload, dispatch_in_batches
from _release.summary import build_summary
from _release import validation as v


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
        packages = [f"pkg{i}" for i in range(BATCH_SIZE + 5)]
        with patch("_release.dispatch.send_dispatch") as mock_send:
            dispatch_in_batches(packages, "repo", "ref", "prod", "tok")
        assert mock_send.call_count == 2
        first_batch = mock_send.call_args_list[0][0][0]["client_payload"]["packages"]
        second_batch = mock_send.call_args_list[1][0][0]["client_payload"]["packages"]
        assert len(first_batch) == BATCH_SIZE
        assert len(second_batch) == 5

    def test_passes_token(self):
        with patch("_release.dispatch.send_dispatch") as mock_send:
            dispatch_in_batches(["pkg"], "repo", "ref", "dev", "my-token")
        assert mock_send.call_args[0][1] == "my-token"


class TestBuildSummary:
    _results = [
        {"package": "postgres", "version": "1.2.3", "status": v.READY},
        {"package": "mysql", "version": "2.0.0b1", "status": v.PRE_RELEASE},
        {"package": "redis", "version": None, "status": v.NO_VERSION},
        {"package": "pg", "version": "1.0.0", "status": v.HAS_FRAGMENTS},
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

    def test_status_labels(self):
        out = build_summary(
            ["postgres", "mysql", "redis", "pg"],
            self._results,
            mode="auto",
            source_repo="integrations-core",
            ref="sha",
            target="prod",
            dry_run=False,
            dispatched=True,
        )
        assert "✅ Dispatched" in out
        assert "⏭️ Pre-release" in out
        assert "⚠️ No version" in out
        assert "❌ Unreleased" in out

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
