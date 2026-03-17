"""Tests for tag_releases entry-point script."""
from unittest.mock import MagicMock, patch

import pytest

import tag_releases


class TestPackageArgs:
    @pytest.mark.parametrize("manual, expected", [
        ("", ["all"]),
        ("all", ["all"]),
        ("ALL", ["all"]),
        ('["postgres","mysql"]', ["postgres", "mysql"]),
        ("[]", ["all"]),
    ])
    def test_returns_expected(self, manual, expected):
        assert tag_releases._package_args(manual) == expected

    def test_invalid_json_exits(self):
        with pytest.raises(SystemExit):
            tag_releases._package_args("invalid-json")


class TestMain:
    def _run_main(self, monkeypatch, env: dict, side_effects):
        for key, val in env.items():
            monkeypatch.setenv(key, val)
        # Remove any keys not in env that might bleed in from the real environment.
        for key in ("TARGET", "DRY_RUN", "MANUAL_PACKAGES"):
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
        assert expected_flag in mock_run.call_args_list[2].args[0]

    def test_exit_code_3_retries_with_no_fetch(self, monkeypatch):
        side_effects = [
            MagicMock(returncode=0),  # git config user.name
            MagicMock(returncode=0),  # git config user.email
            MagicMock(returncode=3),  # first ddev run → fetch failure
            MagicMock(returncode=0),  # retry with --no-fetch
        ]
        mock_run = self._run_main(monkeypatch, {"TARGET": "dev"}, side_effects)
        retry_call = mock_run.call_args_list[3]
        assert "--no-fetch" in retry_call.args[0]

    @pytest.mark.parametrize("returncode", [0, 2])
    def test_success_exit_codes_do_not_exit(self, monkeypatch, returncode):
        # exit 0 = clean success; exit 2 = nothing new to tag
        self._run_main(monkeypatch, {"TARGET": "dev"}, self._side_effects(returncode))

    def test_exit_code_1_raises_system_exit(self, monkeypatch):
        with pytest.raises(SystemExit) as exc_info:
            self._run_main(monkeypatch, {"TARGET": "dev"}, self._side_effects(1))
        assert exc_info.value.code == 1

    def test_git_config_called_before_ddev(self, monkeypatch):
        mock_run = self._run_main(monkeypatch, {"TARGET": "dev"}, self._side_effects(0))
        calls = mock_run.call_args_list
        assert calls[0].args[0][0] == "git"
        assert calls[1].args[0][0] == "git"
        assert calls[2].args[0][0] == "ddev"
