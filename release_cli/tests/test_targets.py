"""Tests for the targets module."""

import yaml

from release.core import TargetData, TargetGenerator


def test_target_generation():
    """Test generating target data."""
    gen = TargetGenerator("https://my-bucket.s3.amazonaws.com")

    target = gen.generate_target(
        integration="postgres",
        version="23.2.0",
        wheel_digest="abc123",
        wheel_size=100905,
        wheel_filename="datadog_postgres-23.2.0-py3-none-any.whl",
        attestation_digest="def456",
    )

    assert target.integration == "postgres"
    assert target.version == "23.2.0"
    assert target.digest == "abc123"
    assert target.length == 100905
    assert target.wheel_path == "/wheels/datadog-postgres/datadog_postgres-23.2.0-py3-none-any.whl"
    assert target.attestation_path == "/attestations/def456.json"


def test_write_target(tmp_path):
    """Test writing target file."""
    gen = TargetGenerator("https://my-bucket.s3.amazonaws.com")

    target_data = TargetData(
        integration="postgres",
        version="23.2.0",
        digest="abc123",
        length=100905,
        repository="https://my-bucket.s3.amazonaws.com",
        wheel_path="/wheels/datadog-postgres/datadog_postgres-23.2.0-py3-none-any.whl",
        attestation_path="/attestations/def456.json",
    )

    target_file = gen.write_target(target_data, tmp_path)

    # Verify file was created in correct location
    expected_file = tmp_path / "datadog-postgres" / "23.2.0.yaml"
    assert target_file == expected_file
    assert target_file.exists()

    # Verify content
    with open(target_file) as f:
        content = yaml.safe_load(f)

    assert content["version"] == "23.2.0"
    assert content["digest"] == "abc123"
    assert content["length"] == 100905
    assert content["attestation_path"] == "/attestations/def456.json"
