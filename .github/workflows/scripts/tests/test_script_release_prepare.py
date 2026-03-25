"""Tests for release_prepare entry-point script."""
import json
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

import release_prepare
from _release.validation import HAS_FRAGMENTS, STABLE


def _stable_result(package: str = "postgres", dispatch: bool = True) -> list[dict]:
    return [{"package": package, "version": "1.0.0", "type": STABLE, "dispatch": dispatch}]


# ---------------------------------------------------------------------------
# _package_args
# ---------------------------------------------------------------------------

class TestPackageArgs:
    @pytest.mark.parametrize("selected, expected", [
        ("", ["all"]),
        ("all", ["all"]),
        ("ALL", ["all"]),
        ('["postgres","mysql"]', ["postgres", "mysql"]),
        ("[]", ["all"]),
    ])
    def test_returns_expected(self, selected, expected):
        assert release_prepare._package_args(selected) == expected

    def test_invalid_json_exits(self):
        with pytest.raises(SystemExit):
            release_prepare._package_args("invalid-json")


# ---------------------------------------------------------------------------
# _parse_is_stable_release
# ---------------------------------------------------------------------------

class TestParseIsStableRelease:
    @pytest.mark.parametrize("env_val, expected", [
        ("false", False),
        ("true", True),
        ("TRUE", True),
        (None, True),  # unset → defaults to True
    ])
    def test_parse(self, monkeypatch, env_val, expected):
        if env_val is None:
            monkeypatch.delenv("IS_STABLE_RELEASE", raising=False)
        else:
            monkeypatch.setenv("IS_STABLE_RELEASE", env_val)
        assert release_prepare._parse_is_stable_release() is expected


# ---------------------------------------------------------------------------
# _tag
# ---------------------------------------------------------------------------

class TestTag:
    _GIT_NAME = call(["git", "config", "user.name", "github-actions[bot]"], check=True)
    _GIT_EMAIL = call(
        ["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"],
        check=True,
    )

    def _run_tag(self, dry_run: bool, selected: str, side_effects):
        with patch("release_prepare.subprocess.run", side_effect=side_effects) as mock_run:
            release_prepare._tag(dry_run, selected)
        return mock_run

    def _side_effects(self, ddev_returncode: int = 0):
        return [
            MagicMock(returncode=0),  # git config user.name
            MagicMock(returncode=0),  # git config user.email
            MagicMock(returncode=ddev_returncode),  # ddev release tag
        ]

    @pytest.mark.parametrize("dry_run, expected_flag", [
        (False, "--push"),
        (True, "--no-push"),
    ])
    def test_push_flag(self, dry_run, expected_flag):
        mock_run = self._run_tag(dry_run, "", self._side_effects(0))
        assert mock_run.mock_calls == [
            self._GIT_NAME,
            self._GIT_EMAIL,
            call(["ddev", "release", "tag", "all", "--skip-prerelease", expected_flag]),
        ]

    def test_exit_code_3_retries_with_no_fetch(self):
        side_effects = [
            MagicMock(returncode=0),  # git config user.name
            MagicMock(returncode=0),  # git config user.email
            MagicMock(returncode=3),  # first ddev run → fetch failure
            MagicMock(returncode=0),  # retry with --no-fetch
        ]
        mock_run = self._run_tag(False, "", side_effects)
        assert mock_run.mock_calls == [
            self._GIT_NAME,
            self._GIT_EMAIL,
            call(["ddev", "release", "tag", "all", "--skip-prerelease", "--push"]),
            call(["ddev", "release", "tag", "all", "--skip-prerelease", "--push", "--no-fetch"]),
        ]

    @pytest.mark.parametrize("returncode", [0, 2])
    def test_success_exit_codes_do_not_exit(self, returncode):
        self._run_tag(False, "", self._side_effects(returncode))

    def test_exit_code_1_raises_system_exit(self):
        with pytest.raises(SystemExit) as exc_info:
            self._run_tag(False, "", self._side_effects(1))
        assert exc_info.value.code == 1

    def test_retry_also_fails_raises_system_exit(self):
        side_effects = [
            MagicMock(returncode=0),  # git config user.name
            MagicMock(returncode=0),  # git config user.email
            MagicMock(returncode=3),  # first ddev run → triggers retry
            MagicMock(returncode=1),  # retry with --no-fetch also fails
        ]
        with patch("release_prepare.subprocess.run", side_effect=side_effects) as mock_run, \
             pytest.raises(SystemExit) as exc_info:
            release_prepare._tag(False, "")
        assert exc_info.value.code == 1
        assert mock_run.mock_calls == [
            self._GIT_NAME,
            self._GIT_EMAIL,
            call(["ddev", "release", "tag", "all", "--skip-prerelease", "--push"]),
            call(["ddev", "release", "tag", "all", "--skip-prerelease", "--push", "--no-fetch"]),
        ]


# ---------------------------------------------------------------------------
# _detect (via main, through the detect logic)
# ---------------------------------------------------------------------------

class TestDetect:
    def test_no_packages_returns_empty(self):
        with patch("release_prepare.get_all_packages", return_value=[]), \
             patch("release_prepare.resolve_packages", return_value=([], "auto-detect from tags at HEAD")):
            packages, mode = release_prepare._detect("")
        assert packages == []
        assert mode == "auto-detect from tags at HEAD"

    def test_packages_detected_returns_list(self):
        pkgs = ["postgres", "mysql"]
        with patch("release_prepare.get_all_packages", return_value=pkgs), \
             patch("release_prepare.resolve_packages", return_value=(pkgs, "auto-detect from tags at HEAD")):
            packages, _ = release_prepare._detect("")
        assert packages == pkgs

    def test_resolve_error_exits(self):
        with patch("release_prepare.get_all_packages", return_value=[]), \
             patch("release_prepare.resolve_packages", side_effect=ValueError("bad")), \
             pytest.raises(SystemExit):
            release_prepare._detect("")


# ---------------------------------------------------------------------------
# _validate
# ---------------------------------------------------------------------------

class TestValidate:
    def _setup(self, monkeypatch, tmp_path):
        runner_temp = tmp_path / "runner_temp"
        runner_temp.mkdir()
        summary_file = tmp_path / "summary"
        monkeypatch.setenv("RUNNER_TEMP", str(runner_temp))
        monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))
        return runner_temp, summary_file

    def test_integrations_core_calls_ddev_validate_version(self, monkeypatch, tmp_path):
        _, _ = self._setup(monkeypatch, tmp_path)
        with patch("release_prepare.subprocess.run", return_value=MagicMock(returncode=0)) as mock_run, \
             patch("release_prepare.validate_packages", return_value=_stable_result()):
            release_prepare._validate(["postgres"], "auto", "integrations-core", "abc123", False, True)
        assert mock_run.mock_calls == [call(["ddev", "validate", "version", "postgres"])]

    def test_integrations_extras_skips_ddev_validate_version(self, monkeypatch, tmp_path):
        self._setup(monkeypatch, tmp_path)
        with patch("release_prepare.subprocess.run") as mock_run, \
             patch("release_prepare.validate_packages", return_value=_stable_result()):
            release_prepare._validate(["postgres"], "auto", "integrations-extras", "abc123", False, True)
        mock_run.assert_not_called()

    def test_ddev_nonzero_exits(self, monkeypatch, tmp_path):
        self._setup(monkeypatch, tmp_path)
        with patch("release_prepare.subprocess.run", return_value=MagicMock(returncode=2)), \
             pytest.raises(SystemExit) as exc_info:
            release_prepare._validate(["postgres"], "auto", "integrations-core", "abc123", False, True)
        assert exc_info.value.code == 2

    def test_stable_on_pre_release_branch_exits(self, monkeypatch, tmp_path):
        _, summary_file = self._setup(monkeypatch, tmp_path)
        with patch("release_prepare.validate_packages", return_value=_stable_result(dispatch=False)), \
             pytest.raises(SystemExit) as exc_info:
            release_prepare._validate(["postgres"], "auto", "integrations-extras", "abc123", False, False)
        assert exc_info.value.code == 1
        assert len(summary_file.read_text()) > 0

    def test_package_with_fragments_exits_and_writes_summary(self, monkeypatch, tmp_path):
        _, summary_file = self._setup(monkeypatch, tmp_path)
        fragment_result = [{"package": "postgres", "version": "1.0.0", "type": HAS_FRAGMENTS, "dispatch": False}]
        with patch("release_prepare.validate_packages", return_value=fragment_result), \
             pytest.raises(SystemExit) as exc_info:
            release_prepare._validate(["postgres"], "auto", "integrations-extras", "abc123", False, True)
        assert exc_info.value.code == 1
        assert len(summary_file.read_text()) > 0

    def test_successful_validation_writes_json(self, monkeypatch, tmp_path):
        runner_temp, _ = self._setup(monkeypatch, tmp_path)
        with patch("release_prepare.validate_packages", return_value=_stable_result()):
            release_prepare._validate(["postgres"], "auto", "integrations-extras", "abc123", False, True)
        data = json.loads((runner_temp / "release_validation.json").read_text())
        assert data["mode"] == "auto"
        assert data["ref"] == "abc123"
        assert "target" not in data


# ---------------------------------------------------------------------------
# main — integration across tag + detect + validate
# ---------------------------------------------------------------------------

class TestMain:
    _GIT_NAME = call(["git", "config", "user.name", "github-actions[bot]"], check=True)
    _GIT_EMAIL = call(
        ["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"],
        check=True,
    )

    def _setup_env(self, monkeypatch, tmp_path, extra: dict | None = None):
        github_output = tmp_path / "github_output"
        github_output.write_text("")
        github_summary = tmp_path / "github_summary"
        github_summary.write_text("")
        runner_temp = tmp_path / "runner_temp"
        runner_temp.mkdir()

        env = {
            "DRY_RUN": "false",
            "SELECTED_PACKAGES": "",
            "SOURCE_REPO": "integrations-extras",
            "REF": "abc123",
            "IS_STABLE_RELEASE": "true",
            "GITHUB_OUTPUT": str(github_output),
            "GITHUB_STEP_SUMMARY": str(github_summary),
            "RUNNER_TEMP": str(runner_temp),
        }
        if extra:
            env.update(extra)
        for key, val in env.items():
            monkeypatch.setenv(key, val)
        return github_output, github_summary, runner_temp

    def _read_outputs(self, github_output: Path) -> dict:
        result = {}
        for line in github_output.read_text().splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                result[key] = value
        return result

    def _git_side_effects(self, ddev_returncode: int = 0):
        return [
            MagicMock(returncode=0),  # git config user.name
            MagicMock(returncode=0),  # git config user.email
            MagicMock(returncode=ddev_returncode),  # ddev release tag
        ]

    def test_no_packages_writes_false_and_summary(self, monkeypatch, tmp_path):
        github_output, github_summary, _ = self._setup_env(monkeypatch, tmp_path)
        with patch("release_prepare.subprocess.run", side_effect=self._git_side_effects()), \
             patch("release_prepare.get_all_packages", return_value=[]), \
             patch("release_prepare.resolve_packages", return_value=([], "auto-detect from tags at HEAD")):
            release_prepare.main()
        outputs = self._read_outputs(github_output)
        assert outputs["has_packages"] == "false"
        assert "No packages detected" in github_summary.read_text()

    def test_packages_detected_writes_outputs(self, monkeypatch, tmp_path):
        github_output, _, _ = self._setup_env(monkeypatch, tmp_path)
        pkgs = ["postgres"]
        with patch("release_prepare.subprocess.run", side_effect=self._git_side_effects()), \
             patch("release_prepare.get_all_packages", return_value=pkgs), \
             patch("release_prepare.resolve_packages", return_value=(pkgs, "auto-detect from tags at HEAD")), \
             patch("release_prepare.validate_packages", return_value=_stable_result()):
            release_prepare.main()
        outputs = self._read_outputs(github_output)
        assert outputs["has_packages"] == "true"
        assert json.loads(outputs["packages"]) == pkgs

    def test_tag_failure_exits_before_detect(self, monkeypatch, tmp_path):
        self._setup_env(monkeypatch, tmp_path)
        side_effects = [
            MagicMock(returncode=0),  # git config user.name
            MagicMock(returncode=0),  # git config user.email
            MagicMock(returncode=1),  # ddev release tag fails
        ]
        with patch("release_prepare.subprocess.run", side_effect=side_effects), \
             patch("release_prepare.get_all_packages") as mock_detect, \
             pytest.raises(SystemExit):
            release_prepare.main()
        mock_detect.assert_not_called()

    def test_dry_run_uses_no_push_flag(self, monkeypatch, tmp_path):
        self._setup_env(monkeypatch, tmp_path, extra={"DRY_RUN": "true"})
        pkgs = ["postgres"]
        with patch("release_prepare.subprocess.run", side_effect=self._git_side_effects()) as mock_run, \
             patch("release_prepare.get_all_packages", return_value=pkgs), \
             patch("release_prepare.resolve_packages", return_value=(pkgs, "auto-detect from tags at HEAD")), \
             patch("release_prepare.validate_packages", return_value=_stable_result()):
            release_prepare.main()
        ddev_call = mock_run.mock_calls[2]
        assert "--no-push" in ddev_call.args[0]

    def test_validate_failure_exits_from_main(self, monkeypatch, tmp_path):
        self._setup_env(monkeypatch, tmp_path)
        pkgs = ["postgres"]
        fragment_result = [{"package": "postgres", "version": "1.0.0", "type": HAS_FRAGMENTS, "dispatch": False}]
        with patch("release_prepare.subprocess.run", side_effect=self._git_side_effects()), \
             patch("release_prepare.get_all_packages", return_value=pkgs), \
             patch("release_prepare.resolve_packages", return_value=(pkgs, "auto-detect from tags at HEAD")), \
             patch("release_prepare.validate_packages", return_value=fragment_result), \
             pytest.raises(SystemExit) as exc_info:
            release_prepare.main()
        assert exc_info.value.code == 1
