"""Tests for the builder module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from release.core import IntegrationBuilder


def test_detect_version(tmp_path):
    """Test version detection from __about__.py."""
    integration_dir = tmp_path / "postgres" / "datadog_checks" / "postgres"
    integration_dir.mkdir(parents=True)
    (integration_dir / "__about__.py").write_text('__version__ = "23.2.0"\n')

    builder = IntegrationBuilder(tmp_path)
    assert builder.detect_version("postgres") == "23.2.0"


@patch("release.core.subprocess.run")
def test_build_wheel(mock_run, tmp_path):
    """Test wheel building."""
    integration_dir = tmp_path / "postgres"
    dist_dir = integration_dir / "dist"
    dist_dir.mkdir(parents=True)

    wheel_file = dist_dir / "datadog_postgres-23.2.0-py3-none-any.whl"
    wheel_file.write_text("fake wheel")

    mock_run.return_value = MagicMock(returncode=0)

    builder = IntegrationBuilder(tmp_path)
    result = builder.build_wheel("postgres")

    assert result == wheel_file


@patch.object(IntegrationBuilder, "build_wheel")
@patch.object(IntegrationBuilder, "detect_version")
def test_build_full(mock_detect, mock_build, tmp_path):
    """Test the full build process."""
    wheel_file = tmp_path / "datadog_postgres-23.2.0-py3-none-any.whl"
    wheel_file.write_bytes(b"fake wheel content")

    mock_detect.return_value = "23.2.0"
    mock_build.return_value = wheel_file

    builder = IntegrationBuilder(tmp_path)
    result = builder.build("postgres")

    assert result.integration == "postgres"
    assert result.version == "23.2.0"
    assert result.wheel_path == wheel_file
    assert len(result.wheel_digest) == 64
