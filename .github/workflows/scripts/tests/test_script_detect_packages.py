"""Tests for detect_packages entry-point script."""
import json
from pathlib import Path
from unittest.mock import patch

import detect_packages



class TestMain:
    def _setup_env(self, monkeypatch, tmp_path, manual_packages: str = ""):
        github_output = tmp_path / "github_output"
        github_output.write_text("")
        github_summary = tmp_path / "github_summary"
        github_summary.write_text("")
        monkeypatch.setenv("GITHUB_OUTPUT", str(github_output))
        monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(github_summary))
        monkeypatch.setenv("MANUAL_PACKAGES", manual_packages)
        return github_output, github_summary

    def _read_outputs(self, github_output: Path) -> dict:
        result = {}
        for line in github_output.read_text().splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                result[key] = value
        return result

    def test_no_packages_writes_false(self, monkeypatch, tmp_path):
        github_output, _ = self._setup_env(monkeypatch, tmp_path)
        with patch("detect_packages.get_all_packages", return_value=[]), \
             patch("detect_packages.resolve_packages", return_value=([], "auto-detect from tags at HEAD")):
            detect_packages.main()
        outputs = self._read_outputs(github_output)
        assert outputs["has_packages"] == "false"

    def test_no_packages_writes_summary(self, monkeypatch, tmp_path):
        _, github_summary = self._setup_env(monkeypatch, tmp_path)
        with patch("detect_packages.get_all_packages", return_value=[]), \
             patch("detect_packages.resolve_packages", return_value=([], "auto-detect from tags at HEAD")):
            detect_packages.main()
        assert "No packages detected" in github_summary.read_text()

    def test_packages_detected_writes_true(self, monkeypatch, tmp_path):
        github_output, _ = self._setup_env(monkeypatch, tmp_path)
        packages = ["postgres", "mysql"]
        with patch("detect_packages.get_all_packages", return_value=packages), \
             patch("detect_packages.resolve_packages", return_value=(packages, "auto-detect from tags at HEAD")):
            detect_packages.main()
        outputs = self._read_outputs(github_output)
        assert outputs["has_packages"] == "true"
        assert json.loads(outputs["packages"]) == packages
        assert outputs["mode"] == "auto-detect from tags at HEAD"

    def test_manual_packages_all_forwards_all(self, monkeypatch, tmp_path):
        all_packages = ["a", "b", "c"]
        github_output, _ = self._setup_env(monkeypatch, tmp_path, manual_packages="all")
        with patch("detect_packages.get_all_packages", return_value=all_packages), \
             patch("detect_packages.resolve_packages", return_value=(all_packages, f"all ({len(all_packages)} packages in repo)")):
            detect_packages.main()
        outputs = self._read_outputs(github_output)
        assert json.loads(outputs["packages"]) == all_packages

    def test_manual_packages_json_forwards_exact_list(self, monkeypatch, tmp_path):
        github_output, _ = self._setup_env(monkeypatch, tmp_path, manual_packages='["postgres"]')
        all_packages = ["postgres", "mysql"]
        with patch("detect_packages.get_all_packages", return_value=all_packages), \
             patch("detect_packages.resolve_packages", return_value=(["postgres"], 'manual (["postgres"])')):
            detect_packages.main()
        outputs = self._read_outputs(github_output)
        assert json.loads(outputs["packages"]) == ["postgres"]
