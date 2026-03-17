"""Tests for validate_release entry-point script."""
import json
from unittest.mock import MagicMock, patch

import pytest

import validate_release
from _release.validation import HAS_FRAGMENTS, STABLE


class TestParseIsStableRelease:
    @pytest.mark.parametrize("env_val, expected", [
        ("false", False),
        ("true", True),
        ("TRUE", True),
        (None, True),   # unset → defaults to True
    ])
    def test_parse(self, monkeypatch, env_val, expected):
        if env_val is None:
            monkeypatch.delenv("IS_STABLE_RELEASE", raising=False)
        else:
            monkeypatch.setenv("IS_STABLE_RELEASE", env_val)
        assert validate_release._parse_is_stable_release() is expected


class TestMain:
    def _base_env(self, monkeypatch, tmp_path, **overrides):
        runner_temp = tmp_path / "runner_temp"
        runner_temp.mkdir()
        summary_file = tmp_path / "summary"

        env = {
            "PACKAGES": '["postgres"]',
            "SOURCE_REPO": "integrations-extras",
            "REF": "abc123",
            "TARGET": "prod",
            "DRY_RUN": "false",
            "IS_STABLE_RELEASE": "true",
            "MODE": "auto",
            "RUNNER_TEMP": str(runner_temp),
            "GITHUB_STEP_SUMMARY": str(summary_file),
        }
        env.update(overrides)
        for key, val in env.items():
            monkeypatch.setenv(key, val)
        return runner_temp, summary_file

    def _stable_result(self, package="postgres", dispatch=True):
        return [{"package": package, "version": "1.0.0", "type": STABLE, "dispatch": dispatch}]

    def test_integrations_core_calls_ddev_validate_version(self, monkeypatch, tmp_path):
        self._base_env(monkeypatch, tmp_path, SOURCE_REPO="integrations-core")
        with patch("validate_release.subprocess.run", return_value=MagicMock(returncode=0)) as mock_run, \
             patch("validate_release.validate_packages", return_value=self._stable_result()):
            validate_release.main()
        ddev_call = mock_run.call_args_list[0]
        assert ddev_call.args[0][:3] == ["ddev", "validate", "version"]

    def test_integrations_extras_skips_ddev_validate_version(self, monkeypatch, tmp_path):
        self._base_env(monkeypatch, tmp_path, SOURCE_REPO="integrations-extras")
        with patch("validate_release.subprocess.run") as mock_run, \
             patch("validate_release.validate_packages", return_value=self._stable_result()):
            validate_release.main()
        mock_run.assert_not_called()

    def test_ddev_nonzero_exits(self, monkeypatch, tmp_path):
        self._base_env(monkeypatch, tmp_path, SOURCE_REPO="integrations-core")
        with patch("validate_release.subprocess.run", return_value=MagicMock(returncode=2)), \
             pytest.raises(SystemExit) as exc_info:
            validate_release.main()
        assert exc_info.value.code == 2

    def test_stable_on_pre_release_branch_exits(self, monkeypatch, tmp_path):
        _, summary_file = self._base_env(monkeypatch, tmp_path, SOURCE_REPO="integrations-extras", IS_STABLE_RELEASE="false")
        with patch("validate_release.validate_packages", return_value=self._stable_result(dispatch=False)), \
             pytest.raises(SystemExit) as exc_info:
            validate_release.main()
        assert exc_info.value.code == 1
        assert len(summary_file.read_text()) > 0

    def test_package_with_fragments_exits_and_writes_summary(self, monkeypatch, tmp_path):
        _, summary_file = self._base_env(monkeypatch, tmp_path)
        fragment_result = [{"package": "postgres", "version": "1.0.0", "type": HAS_FRAGMENTS, "dispatch": False}]
        with patch("validate_release.validate_packages", return_value=fragment_result), \
             pytest.raises(SystemExit) as exc_info:
            validate_release.main()
        assert exc_info.value.code == 1
        assert len(summary_file.read_text()) > 0

    def test_successful_validation_writes_json(self, monkeypatch, tmp_path):
        runner_temp, _ = self._base_env(monkeypatch, tmp_path)
        with patch("validate_release.validate_packages", return_value=self._stable_result()):
            validate_release.main()
        validation_file = runner_temp / "release_validation.json"
        assert validation_file.exists()
        data = json.loads(validation_file.read_text())
        assert "results" in data
        assert "mode" in data
        assert "ref" in data
        assert "target" in data
        assert "dry_run" in data
