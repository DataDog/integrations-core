"""Tests for release_dispatch entry-point script."""
import json
from pathlib import Path
from unittest.mock import call, patch

import release_dispatch


def _write_validation(path: Path, dry_run: bool = False) -> None:
    data = {
        "results": [],
        "mode": "auto",
        "ref": "abc123",
        "target": "prod",
        "dry_run": dry_run,
    }
    path.write_text(json.dumps(data))


class TestLoadValidation:
    def test_file_present_returns_dict(self, tmp_path):
        validation_file = tmp_path / "release_validation.json"
        _write_validation(validation_file)
        result = release_dispatch._load_validation(str(tmp_path))
        assert result["mode"] == "auto"
        assert result["dry_run"] is False

    def test_file_absent_returns_empty_dict(self, tmp_path, capsys):
        result = release_dispatch._load_validation(str(tmp_path))
        assert result == {}
        assert "Warning" in capsys.readouterr().err

    def test_invalid_json_returns_empty_dict(self, tmp_path, capsys):
        (tmp_path / "release_validation.json").write_text("not-valid-json{")
        result = release_dispatch._load_validation(str(tmp_path))
        assert result == {}
        assert "Warning" in capsys.readouterr().err


class TestMain:
    def _base_env(self, monkeypatch, tmp_path, dry_run: bool = False, write_validation: bool = True):
        runner_temp = tmp_path / "runner_temp"
        runner_temp.mkdir()
        if write_validation:
            _write_validation(runner_temp / "release_validation.json", dry_run=dry_run)

        summary_file = tmp_path / "summary"

        monkeypatch.setenv("PACKAGES", '["postgres", "mysql"]')
        monkeypatch.setenv("SOURCE_REPO", "integrations-core")
        monkeypatch.setenv("REF", "abc123")
        monkeypatch.setenv("TARGET", "prod")
        monkeypatch.setenv("GH_TOKEN", "test-token")
        monkeypatch.setenv("RUNNER_TEMP", str(runner_temp))
        monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))
        return runner_temp, summary_file

    def test_dry_run_does_not_dispatch(self, monkeypatch, tmp_path):
        self._base_env(monkeypatch, tmp_path, dry_run=True)
        with patch("release_dispatch.dispatch_in_batches") as mock_dispatch, \
             patch("release_dispatch.write_summary"):
            release_dispatch.main()
        mock_dispatch.assert_not_called()

    def test_dry_run_writes_summary(self, monkeypatch, tmp_path):
        self._base_env(monkeypatch, tmp_path, dry_run=True)
        with patch("release_dispatch.dispatch_in_batches"), \
             patch("release_dispatch.write_summary") as mock_summary:
            release_dispatch.main()
        mock_summary.assert_called_once()

    def test_non_dry_run_calls_dispatch_in_batches(self, monkeypatch, tmp_path):
        self._base_env(monkeypatch, tmp_path, dry_run=False)
        with patch("release_dispatch.dispatch_in_batches") as mock_dispatch, \
             patch("release_dispatch.write_summary"):
            release_dispatch.main()
        assert mock_dispatch.mock_calls == [
            call(["postgres", "mysql"], "integrations-core", "abc123", "prod", "test-token"),
        ]

    def test_missing_validation_file_still_runs(self, monkeypatch, tmp_path):
        self._base_env(monkeypatch, tmp_path, write_validation=False)
        monkeypatch.setenv("DRY_RUN", "false")
        with patch("release_dispatch.dispatch_in_batches") as mock_dispatch, \
             patch("release_dispatch.write_summary"):
            release_dispatch.main()
        mock_dispatch.assert_called_once()
