"""Tests for _release.packages."""
import pytest

from _release.packages import detect_from_tags, get_all_packages, resolve_packages


class TestGetAllPackages:
    def test_finds_packages(self, tmp_path):
        for name in ("postgres", "mysql", "redis"):
            about = tmp_path / name / "datadog_checks" / name / "__about__.py"
            about.parent.mkdir(parents=True)
            about.write_text('__version__ = "1.0.0"\n')

        result = get_all_packages(tmp_path)
        assert result == ["mysql", "postgres", "redis"]

    def test_empty_repo(self, tmp_path):
        assert get_all_packages(tmp_path) == []


class TestDetectFromTags:
    def test_strips_version_suffix(self):
        tags = ["postgres-1.2.3", "mysql-0.1.0", "redis-10.0.0"]
        assert detect_from_tags(tags) == ["mysql", "postgres", "redis"]

    def test_deduplicates(self):
        tags = ["postgres-1.2.3", "postgres-1.2.4"]
        assert detect_from_tags(tags) == ["postgres"]

    def test_ignores_blank_lines(self):
        tags = ["postgres-1.2.3", "", "  ", "mysql-2.0.0"]
        assert detect_from_tags(tags) == ["mysql", "postgres"]

    def test_empty_list(self):
        assert detect_from_tags([]) == []

    def test_pre_release_version_stripped(self):
        # e.g. datadog_checks_base-7.0.0rc1
        tags = ["datadog_checks_base-7.0.0rc1"]
        assert detect_from_tags(tags) == ["datadog_checks_base"]

    def test_hyphenated_package_name(self):
        # The regex strips from the LAST -X.Y.Z occurrence
        tags = ["amazon-msk-1.2.3"]
        assert detect_from_tags(tags) == ["amazon-msk"]


class TestResolvePackages:
    ALL = ["mysql", "postgres", "redis"]

    def test_all_keyword(self):
        packages, mode = resolve_packages("all", self.ALL)
        assert packages == self.ALL
        assert "all" in mode
        assert str(len(self.ALL)) in mode

    def test_all_keyword_case_insensitive(self):
        packages, _ = resolve_packages("ALL", self.ALL)
        assert packages == self.ALL

    def test_json_array(self):
        packages, mode = resolve_packages('["postgres","mysql"]', self.ALL)
        assert packages == ["postgres", "mysql"]
        assert "manual" in mode

    def test_auto_detect(self):
        tags = ["postgres-1.0.0", "redis-2.0.0"]
        packages, mode = resolve_packages("", self.ALL, head_tags=tags)
        assert packages == ["postgres", "redis"]
        assert "auto-detect" in mode

    def test_unknown_package_exits(self):
        with pytest.raises(SystemExit):
            resolve_packages('["unknown_pkg"]', self.ALL)

    def test_invalid_json_exits(self):
        with pytest.raises(SystemExit):
            resolve_packages("not-json", self.ALL)

    def test_unknown_in_auto_detect_exits(self):
        tags = ["not-a-package-1.0.0"]
        with pytest.raises(SystemExit):
            resolve_packages("", self.ALL, head_tags=tags)
