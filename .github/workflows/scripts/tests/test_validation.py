"""Tests for _release.validation."""
from pathlib import Path

import pytest

from _release.validation import (
    HAS_FRAGMENTS,
    NO_VERSION,
    PRE_RELEASE,
    READY,
    get_version,
    has_changelog_fragments,
    is_pre_release,
    validate_package,
    validate_packages,
)


def _make_package(root: Path, name: str, version: str) -> Path:
    """Create a minimal package directory under *root*."""
    about = root / name / "datadog_checks" / name / "__about__.py"
    about.parent.mkdir(parents=True)
    about.write_text(f'__version__ = "{version}"\n')
    return root / name


class TestGetVersion:
    def test_reads_version(self, tmp_path):
        _make_package(tmp_path, "postgres", "1.2.3")
        assert get_version("postgres", tmp_path) == "1.2.3"

    def test_missing_about_returns_none(self, tmp_path):
        (tmp_path / "postgres").mkdir()
        assert get_version("postgres", tmp_path) is None

    def test_missing_package_returns_none(self, tmp_path):
        assert get_version("nonexistent", tmp_path) is None

    def test_version_with_pre_release(self, tmp_path):
        _make_package(tmp_path, "pkg", "2.0.0rc1")
        assert get_version("pkg", tmp_path) == "2.0.0rc1"


class TestIsPreRelease:
    @pytest.mark.parametrize("version", ["1.0.0a1", "2.0.0b3", "3.0.0rc2"])
    def test_pre_release_versions(self, version):
        assert is_pre_release(version) is True

    @pytest.mark.parametrize("version", ["1.0.0", "2.3.4", "10.0.1"])
    def test_stable_versions(self, version):
        assert is_pre_release(version) is False


class TestHasChangelogFragments:
    def test_no_changelog_dir(self, tmp_path):
        _make_package(tmp_path, "pkg", "1.0.0")
        assert has_changelog_fragments("pkg", tmp_path) is False

    def test_empty_changelog_dir(self, tmp_path):
        _make_package(tmp_path, "pkg", "1.0.0")
        (tmp_path / "pkg" / "changelog.d").mkdir()
        assert has_changelog_fragments("pkg", tmp_path) is False

    def test_gitkeep_is_ignored(self, tmp_path):
        """Bug fix: .gitkeep must NOT be counted as a changelog fragment."""
        _make_package(tmp_path, "pkg", "1.0.0")
        changelog_d = tmp_path / "pkg" / "changelog.d"
        changelog_d.mkdir()
        (changelog_d / ".gitkeep").write_text("")
        assert has_changelog_fragments("pkg", tmp_path) is False

    def test_readme_is_ignored(self, tmp_path):
        _make_package(tmp_path, "pkg", "1.0.0")
        changelog_d = tmp_path / "pkg" / "changelog.d"
        changelog_d.mkdir()
        (changelog_d / "README.md").write_text("# Changelog fragments\n")
        assert has_changelog_fragments("pkg", tmp_path) is False

    def test_valid_fragment_detected(self, tmp_path):
        _make_package(tmp_path, "pkg", "1.0.0")
        changelog_d = tmp_path / "pkg" / "changelog.d"
        changelog_d.mkdir()
        (changelog_d / "1234.fixed").write_text("Fixed a bug.")
        assert has_changelog_fragments("pkg", tmp_path) is True

    def test_added_fragment_detected(self, tmp_path):
        _make_package(tmp_path, "pkg", "1.0.0")
        changelog_d = tmp_path / "pkg" / "changelog.d"
        changelog_d.mkdir()
        (changelog_d / "42.added").write_text("Added a feature.")
        assert has_changelog_fragments("pkg", tmp_path) is True

    def test_gitkeep_plus_fragment(self, tmp_path):
        """When a real fragment coexists with .gitkeep, fragments are detected."""
        _make_package(tmp_path, "pkg", "1.0.0")
        changelog_d = tmp_path / "pkg" / "changelog.d"
        changelog_d.mkdir()
        (changelog_d / ".gitkeep").write_text("")
        (changelog_d / "99.changed").write_text("Breaking change.")
        assert has_changelog_fragments("pkg", tmp_path) is True


class TestValidatePackage:
    def test_ready(self, tmp_path):
        _make_package(tmp_path, "pkg", "1.0.0")
        result = validate_package("pkg", tmp_path)
        assert result == {"package": "pkg", "version": "1.0.0", "status": READY}

    def test_no_version(self, tmp_path):
        (tmp_path / "pkg").mkdir()
        result = validate_package("pkg", tmp_path)
        assert result["status"] == NO_VERSION
        assert result["version"] is None

    def test_pre_release(self, tmp_path):
        _make_package(tmp_path, "pkg", "2.0.0b1")
        result = validate_package("pkg", tmp_path)
        assert result["status"] == PRE_RELEASE
        assert result["version"] == "2.0.0b1"

    def test_has_fragments(self, tmp_path):
        _make_package(tmp_path, "pkg", "1.0.0")
        changelog_d = tmp_path / "pkg" / "changelog.d"
        changelog_d.mkdir()
        (changelog_d / "7.fixed").write_text("Fix.")
        result = validate_package("pkg", tmp_path)
        assert result["status"] == HAS_FRAGMENTS

    def test_pre_release_takes_priority_over_fragments(self, tmp_path):
        """Pre-release packages are skipped even if they have fragments."""
        _make_package(tmp_path, "pkg", "1.0.0a1")
        changelog_d = tmp_path / "pkg" / "changelog.d"
        changelog_d.mkdir()
        (changelog_d / "1.fixed").write_text("Fix.")
        result = validate_package("pkg", tmp_path)
        assert result["status"] == PRE_RELEASE


class TestValidatePackages:
    def test_multiple_packages(self, tmp_path):
        _make_package(tmp_path, "a", "1.0.0")
        _make_package(tmp_path, "b", "2.0.0b1")
        results = validate_packages(["a", "b"], tmp_path)
        assert len(results) == 2
        statuses = {r["package"]: r["status"] for r in results}
        assert statuses["a"] == READY
        assert statuses["b"] == PRE_RELEASE
