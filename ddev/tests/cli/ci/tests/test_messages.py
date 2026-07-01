# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the ci/tests pipeline messages."""

from __future__ import annotations

import pytest

from ddev.cli.ci.tests.messages import ARTIFACT_NAME_DISALLOWED, BatchJob, split_artifact_name


def _job(**overrides: object) -> BatchJob:
    base = {
        "name": "job-1",
        "target": "ntp",
        "runner": "ubuntu-latest",
        "environment": "py3.13",
        "platform": "linux",
        "unit_tests": True,
        "e2e_tests": False,
    }
    base.update(overrides)
    return BatchJob(**base)  # type: ignore[arg-type]


def test_artifact_name_is_deterministic() -> None:
    assert _job().artifact_name() == _job().artifact_name()


def test_artifact_name_built_from_target_env_platform() -> None:
    assert _job().artifact_name() == "ntp~py3.13~linux"


def test_artifact_name_is_reversible() -> None:
    # split_artifact_name recovers (target, environment, platform) even when fields contain hyphens.
    job = _job(target="datadog_checks_base", environment="py3.13-18", platform="linux")
    assert split_artifact_name(job.artifact_name()) == ("datadog_checks_base", "py3.13-18", "linux")


def test_split_artifact_name_rejects_unexpected_shape() -> None:
    with pytest.raises(ValueError):
        split_artifact_name("not-a-valid-artifact-name")


@pytest.mark.parametrize("field", ["name", "runner", "unit_tests", "e2e_tests"])
def test_artifact_name_ignores_non_identifying_fields(field: str) -> None:
    # name / runner / unit_tests / e2e_tests are not part of the artifact name.
    changed = {"name": "other-job", "runner": "windows-latest", "unit_tests": False, "e2e_tests": True}[field]
    assert _job(**{field: changed}).artifact_name() == _job().artifact_name()


@pytest.mark.parametrize(
    ("field", "value"),
    [("target", "kafka"), ("environment", "py3.12"), ("platform", "windows")],
)
def test_artifact_name_varies_with_identifying_fields(field: str, value: str) -> None:
    assert _job(**{field: value}).artifact_name() != _job().artifact_name()


def test_artifact_name_sanitizes_disallowed_characters() -> None:
    name = _job(target='a/b:c*d?e|f"g<h>i\\j', environment="x\r\ny").artifact_name()
    assert ARTIFACT_NAME_DISALLOWED.search(name) is None
