"""Tests for tag_releases entry-point script."""
from unittest.mock import MagicMock, call, patch

import pytest

import tag_releases


class TestPackageArgs:
    @pytest.mark.parametrize("selected, expected", [
        ("", ["all"]),
        ("all", ["all"]),
        ("ALL", ["all"]),
        ('["postgres","mysql"]', ["postgres", "mysql"]),
        ("[]", ["all"]),
    ])
    def test_returns_expected(self, selected, expected):
        assert tag_releases._package_args(selected) == expected

    def test_invalid_json_exits(self):
        with pytest.raises(SystemExit):
            tag_releases._package_args("invalid-json")


class TestMain:
    _GIT_NAME = call(["git", "config", "user.name", "github-actions[bot]"], check=True)
    _GIT_EMAIL = call(
        ["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"],
        check=True,
    )

    def _run_main(self, monkeypatch, env: dict, side_effects):
        for key, val in env.items():
            monkeypatch.setenv(key, val)
        # Remove any keys not in env that might bleed in from the real environment.
        for key in ("TARGET", "DRY_RUN", "SELECTED_PACKAGES"):
            if key not in env:
                monkeypatch.delenv(key, raising=False)
        with patch("tag_releases.subprocess.run", side_effect=side_effects) as mock_run:
            tag_releases.main()
        return mock_run

    def _side_effects(self, ddev_returncode: int = 0):
        """Two successful git-config calls then a ddev call."""
        return [
            MagicMock(returncode=0),  # git config user.name
            MagicMock(returncode=0),  # git config user.email
            MagicMock(returncode=ddev_returncode),  # ddev release tag
        ]

    @pytest.mark.parametrize("env, expected_flag", [
        ({"TARGET": "prod", "DRY_RUN": "false"}, "--push"),
        ({"TARGET": "dev"}, "--no-push"),
        ({"TARGET": "prod", "DRY_RUN": "true"}, "--no-push"),
    ])
    def test_push_flag(self, monkeypatch, env, expected_flag):
        mock_run = self._run_main(monkeypatch, env, self._side_effects(0))
        assert mock_run.mock_calls == [
            self._GIT_NAME,
            self._GIT_EMAIL,
            call(["ddev", "release", "tag", "all", "--skip-prerelease", expected_flag]),
        ]

    def test_exit_code_3_retries_with_no_fetch(self, monkeypatch):
        side_effects = [
            MagicMock(returncode=0),  # git config user.name
            MagicMock(returncode=0),  # git config user.email
            MagicMock(returncode=3),  # first ddev run → fetch failure
            MagicMock(returncode=0),  # retry with --no-fetch
        ]
        mock_run = self._run_main(monkeypatch, {"TARGET": "dev"}, side_effects)
        assert mock_run.mock_calls == [
            self._GIT_NAME,
            self._GIT_EMAIL,
            call(["ddev", "release", "tag", "all", "--skip-prerelease", "--no-push"]),
            call(["ddev", "release", "tag", "all", "--skip-prerelease", "--no-push", "--no-fetch"]),
        ]

    @pytest.mark.parametrize("returncode", [0, 2])
    def test_success_exit_codes_do_not_exit(self, monkeypatch, returncode):
        # exit 0 = clean success; exit 2 = nothing new to tag
        self._run_main(monkeypatch, {"TARGET": "dev"}, self._side_effects(returncode))

    def test_exit_code_1_raises_system_exit(self, monkeypatch):
        with pytest.raises(SystemExit) as exc_info:
            self._run_main(monkeypatch, {"TARGET": "dev"}, self._side_effects(1))
        assert exc_info.value.code == 1

    def test_retry_also_fails_raises_system_exit(self, monkeypatch):
        side_effects = [
            MagicMock(returncode=0),  # git config user.name
            MagicMock(returncode=0),  # git config user.email
            MagicMock(returncode=3),  # first ddev run → triggers retry
            MagicMock(returncode=1),  # retry with --no-fetch also fails
        ]
        with patch("tag_releases.subprocess.run", side_effect=side_effects) as mock_run, \
             pytest.raises(SystemExit) as exc_info:
            for key in ("TARGET", "DRY_RUN", "SELECTED_PACKAGES"):
                monkeypatch.delenv(key, raising=False)
            monkeypatch.setenv("TARGET", "dev")
            tag_releases.main()
        assert exc_info.value.code == 1
        assert mock_run.mock_calls == [
            self._GIT_NAME,
            self._GIT_EMAIL,
            call(["ddev", "release", "tag", "all", "--skip-prerelease", "--no-push"]),
            call(["ddev", "release", "tag", "all", "--skip-prerelease", "--no-push", "--no-fetch"]),
        ]

