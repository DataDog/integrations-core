"""Tests for CLI commands."""

import json
from pathlib import Path

from click.testing import CliRunner

from release.cli import cli


def test_validate_integrations_valid():
    """Test validating a valid integrations list."""
    runner = CliRunner()
    result = runner.invoke(cli, ["validate-integrations", '["postgres", "mysql", "redis"]'])

    assert result.exit_code == 0

    output = json.loads(result.output)
    assert output["valid"] is True
    assert output["count"] == 3
    assert output["integrations"] == ["postgres", "mysql", "redis"]


def test_validate_integrations_single():
    """Test validating a single integration."""
    runner = CliRunner()
    result = runner.invoke(cli, ["validate-integrations", '["postgres"]'])

    assert result.exit_code == 0

    output = json.loads(result.output)
    assert output["valid"] is True
    assert output["count"] == 1
    assert output["integrations"] == ["postgres"]


def test_validate_integrations_max_count():
    """Test max count validation."""
    runner = CliRunner()

    # Should succeed with count under max
    result = runner.invoke(cli, ["validate-integrations", '["postgres", "mysql"]', "--max-count", "2"])
    assert result.exit_code == 0

    # Should fail with count over max
    result = runner.invoke(cli, ["validate-integrations", '["postgres", "mysql"]', "--max-count", "1"])
    assert result.exit_code == 1

    output = json.loads(result.output)
    assert output["valid"] is False
    assert "Too many integrations" in output["error"]


def test_validate_integrations_invalid_json():
    """Test with invalid JSON."""
    runner = CliRunner()
    result = runner.invoke(cli, ["validate-integrations", "not-json"])

    assert result.exit_code == 1

    output = json.loads(result.output)
    assert output["valid"] is False
    assert "Invalid JSON" in output["error"]


def test_validate_integrations_not_array():
    """Test with non-array JSON."""
    runner = CliRunner()
    result = runner.invoke(cli, ["validate-integrations", '{"foo": "bar"}'])

    assert result.exit_code == 1

    output = json.loads(result.output)
    assert output["valid"] is False
    assert "Expected JSON array" in output["error"]


def test_validate_integrations_empty_array():
    """Test with empty array."""
    runner = CliRunner()
    result = runner.invoke(cli, ["validate-integrations", "[]"])

    assert result.exit_code == 1

    output = json.loads(result.output)
    assert output["valid"] is False
    assert "cannot be empty" in output["error"]


def test_validate_integrations_non_string_items():
    """Test with non-string items in array."""
    runner = CliRunner()
    result = runner.invoke(cli, ["validate-integrations", '["postgres", 123, "mysql"]'])

    assert result.exit_code == 1

    output = json.loads(result.output)
    assert output["valid"] is False
    assert "not a string" in output["error"]


def test_validate_integrations_empty_string():
    """Test with empty string in array."""
    runner = CliRunner()
    result = runner.invoke(cli, ["validate-integrations", '["postgres", "", "mysql"]'])

    assert result.exit_code == 1

    output = json.loads(result.output)
    assert output["valid"] is False
    assert "empty or whitespace" in output["error"]


def test_validate_integrations_whitespace_string():
    """Test with whitespace-only string in array."""
    runner = CliRunner()
    result = runner.invoke(cli, ["validate-integrations", '["postgres", "   ", "mysql"]'])

    assert result.exit_code == 1

    output = json.loads(result.output)
    assert output["valid"] is False
    assert "empty or whitespace" in output["error"]


def test_organize_targets_success(tmp_path):
    """Test successful organization of target files."""
    runner = CliRunner()

    # Create input structure simulating downloaded artifacts
    # Pattern: targets-raw/target-{integration}-{version}/{integration}/{version}.yaml
    input_dir = tmp_path / "targets-raw"
    postgres_artifact = input_dir / "target-postgres-23.2.0" / "datadog-postgres"
    postgres_artifact.mkdir(parents=True)
    (postgres_artifact / "23.2.0.yaml").write_text("postgres: 23.2.0")

    mysql_artifact = input_dir / "target-mysql-8.0.1" / "datadog-mysql"
    mysql_artifact.mkdir(parents=True)
    (mysql_artifact / "8.0.1.yaml").write_text("mysql: 8.0.1")

    output_dir = tmp_path / "targets-organized"

    # Run organize command
    result = runner.invoke(
        cli,
        [
            "organize-targets",
            "--input-dir",
            str(input_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0

    output = json.loads(result.output)
    assert output["success"] is True
    assert output["files_organized"] == 2

    # Verify files were organized correctly
    assert (output_dir / "datadog-postgres" / "23.2.0.yaml").exists()
    assert (output_dir / "datadog-mysql" / "8.0.1.yaml").exists()

    # Verify content was copied correctly
    assert (output_dir / "datadog-postgres" / "23.2.0.yaml").read_text() == "postgres: 23.2.0"
    assert (output_dir / "datadog-mysql" / "8.0.1.yaml").read_text() == "mysql: 8.0.1"


def test_organize_targets_no_files(tmp_path):
    """Test organization with no target files."""
    runner = CliRunner()

    input_dir = tmp_path / "targets-raw"
    input_dir.mkdir()
    output_dir = tmp_path / "targets-organized"

    result = runner.invoke(
        cli,
        [
            "organize-targets",
            "--input-dir",
            str(input_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 1

    output = json.loads(result.output)
    assert output["success"] is False
    assert "No target files" in output["error"]


def test_organize_targets_nested_structure(tmp_path):
    """Test organization with deeply nested structure."""
    runner = CliRunner()

    # Create a more complex nested structure
    input_dir = tmp_path / "targets-raw"
    nested_path = input_dir / "some" / "nested" / "path" / "datadog-redis"
    nested_path.mkdir(parents=True)
    (nested_path / "1.0.0.yaml").write_text("redis: 1.0.0")

    output_dir = tmp_path / "targets-organized"

    result = runner.invoke(
        cli,
        [
            "organize-targets",
            "--input-dir",
            str(input_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0

    output = json.loads(result.output)
    assert output["success"] is True
    assert output["files_organized"] == 1

    # File should be organized by the parent directory name
    assert (output_dir / "datadog-redis" / "1.0.0.yaml").exists()
    assert (output_dir / "datadog-redis" / "1.0.0.yaml").read_text() == "redis: 1.0.0"


def test_organize_targets_multiple_versions(tmp_path):
    """Test organizing multiple versions of same integration."""
    runner = CliRunner()

    input_dir = tmp_path / "targets-raw"

    # Create multiple versions of postgres
    postgres_v1 = input_dir / "target-postgres-23.1.0" / "datadog-postgres"
    postgres_v1.mkdir(parents=True)
    (postgres_v1 / "23.1.0.yaml").write_text("postgres: 23.1.0")

    postgres_v2 = input_dir / "target-postgres-23.2.0" / "datadog-postgres"
    postgres_v2.mkdir(parents=True)
    (postgres_v2 / "23.2.0.yaml").write_text("postgres: 23.2.0")

    output_dir = tmp_path / "targets-organized"

    result = runner.invoke(
        cli,
        [
            "organize-targets",
            "--input-dir",
            str(input_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0

    output = json.loads(result.output)
    assert output["success"] is True
    assert output["files_organized"] == 2

    # Both versions should be in the same integration directory
    assert (output_dir / "datadog-postgres" / "23.1.0.yaml").exists()
    assert (output_dir / "datadog-postgres" / "23.2.0.yaml").exists()


def test_organize_targets_input_dir_not_exist(tmp_path):
    """Test with non-existent input directory."""
    runner = CliRunner()

    input_dir = tmp_path / "does-not-exist"
    output_dir = tmp_path / "targets-organized"

    result = runner.invoke(
        cli,
        [
            "organize-targets",
            "--input-dir",
            str(input_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    # Click validates path existence, so this should fail before our code runs
    assert result.exit_code != 0
