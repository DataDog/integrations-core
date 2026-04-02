"""Tests for _release.dispatch and _release.summary."""
import pytest

from _release.dispatch import build_batches, build_client_payload
from _release.summary import build_summary, _ineligible_label
from _release import validation as v


class TestBuildClientPayload:
    def test_structure(self):
        payload = build_client_payload(["postgres", "mysql"], "integrations-core", "abc123")
        assert payload["packages"] == ["postgres", "mysql"]
        assert payload["source_repo"] == "integrations-core"
        assert payload["source_repo_ref"] == "abc123"
        assert "target" not in payload
        assert "event_type" not in payload


class TestBuildBatches:
    def test_single_batch(self):
        packages = ["a", "b", "c"]
        batches = build_batches(packages, "integrations-core", "sha1")
        assert batches == [build_client_payload(packages, "integrations-core", "sha1")]

    def test_splits_into_batches(self):
        packages = [f"pkg{i}" for i in range(8)]
        batches = build_batches(packages, "repo", "ref", batch_size=3)
        assert batches == [
            build_client_payload(packages[:3], "repo", "ref"),
            build_client_payload(packages[3:6], "repo", "ref"),
            build_client_payload(packages[6:], "repo", "ref"),
        ]

    def test_empty_packages_returns_empty_list(self):
        assert build_batches([], "repo", "ref") == []

    def test_invalid_batch_size_raises(self):
        with pytest.raises(ValueError):
            build_batches(["pkg"], "repo", "ref", batch_size=0)


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
            dry_run=False,
            was_dispatched=True,
        )
        return build_summary(packages or ["postgres"], self._results, **{**defaults, **kwargs})

    def test_labels_when_dispatched(self):
        out = build_summary(
            ["postgres", "mysql", "redis", "pg", "new_pkg"],
            self._results,
            mode="auto",
            source_repo="integrations-core",
            ref="sha",
            dry_run=False,
            was_dispatched=True,
        )
        assert "✅ Dispatched" in out
        assert "⏭️ Placeholder version" in out
        assert "⚠️ No version" in out
        assert "❌ Pending changelog" in out

    def test_pre_release_dry_run_label(self):
        out = self._summary(packages=["mysql"], dry_run=True, was_dispatched=False)
        assert "🔄 Dry run" in out

    def test_dry_run_label(self):
        out = self._summary(dry_run=True, was_dispatched=False)
        assert "🔄 Dry run" in out

    def test_custom_footer(self):
        out = self._summary(was_dispatched=False, footer="> Custom footer text")
        assert "Custom footer text" in out

    def test_ref_truncated_in_link(self):
        full_sha = "a" * 40
        out = self._summary(ref=full_sha)
        assert full_sha[:12] in out
        assert full_sha[12:] not in out.split("commit/")[0]

    def test_stable_blocked_on_pre_release_branch(self):
        results = [{"package": "postgres", "version": "1.2.3", "type": v.STABLE, "dispatch": False}]
        out = build_summary(
            ["postgres"],
            results,
            mode="auto",
            source_repo="integrations-core",
            ref="sha",
            dry_run=False,
            was_dispatched=False,
        )
        assert "❌ Stable release blocked (pre-release branch)" in out

    def test_pre_release_skipped_on_stable_branch(self):
        results = [{"package": "mysql", "version": "2.0.0b1", "type": v.PRE_RELEASE, "dispatch": False}]
        out = build_summary(
            ["mysql"],
            results,
            mode="auto",
            source_repo="integrations-core",
            ref="sha",
            dry_run=False,
            was_dispatched=False,
        )
        assert "⏭️ Pre-release skipped (stable branch)" in out

    def test_eligible_not_dispatched(self):
        results = [{"package": "postgres", "version": "1.2.3", "type": v.STABLE, "dispatch": True}]
        out = build_summary(
            ["postgres"],
            results,
            mode="auto",
            source_repo="integrations-core",
            ref="sha",
            dry_run=False,
            was_dispatched=False,
        )
        assert "✅ Validated" in out

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="unexpected validation type"):
            _ineligible_label("bogus_type")
