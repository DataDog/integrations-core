"""Tests for _release.packages."""
import pytest
from _release.packages import (detect_from_tags, get_all_packages,
                               resolve_packages)


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
        tags = ["datadog_checks_base-7.0.0rc1"]
        assert detect_from_tags(tags) == ["datadog_checks_base"]

    def test_strips_only_version_suffix(self):
        tags = ["amazon-msk-1.2.3"]
        assert detect_from_tags(tags) == ["amazon-msk"]


class TestResolvePackages:
    all_packages = ["mysql", "postgres", "redis"]

    def test_all_keyword(self):
        packages, mode = resolve_packages(selected="all", all_packages=self.all_packages)
        assert packages == self.all_packages
        assert mode == f"all ({len(self.all_packages)} packages in repo)"

    def test_all_keyword_case_insensitive(self):
        packages, _ = resolve_packages(selected="ALL", all_packages=self.all_packages)
        assert packages == self.all_packages

    def test_json_array(self):
        packages, mode = resolve_packages('["postgres","mysql"]', all_packages=self.all_packages)
        assert packages == ["postgres", "mysql"]
        assert mode == 'manual (["postgres","mysql"])'

    def test_auto_detect(self):
        tags = ["postgres-1.0.0", "redis-2.0.0"]
        packages, mode = resolve_packages(selected="", all_packages=self.all_packages, head_tags=tags)
        assert packages == ["postgres", "redis"]
        assert mode == "auto-detect from tags at HEAD"

    def test_unknown_package_exits(self):
        with pytest.raises(SystemExit):
            resolve_packages('["unknown_pkg"]', all_packages=self.all_packages)

    def test_invalid_json_exits(self):
        with pytest.raises(SystemExit):
            resolve_packages(selected="not-json", all_packages=self.all_packages)

    def test_unknown_in_auto_detect_exits(self):
        tags = ["not-a-package-1.0.0"]
        with pytest.raises(SystemExit):
            resolve_packages(selected="", all_packages=self.all_packages, head_tags=tags)
