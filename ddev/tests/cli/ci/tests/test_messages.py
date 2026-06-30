# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the ci/tests pipeline messages."""

from __future__ import annotations

import dataclasses

from ddev.cli.ci.tests.messages import ARTIFACT_NAME_DISALLOWED, ARTIFACT_NAME_MAX_LENGTH, BatchJob


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
    job = _job()
    assert job.artifact_name() == job.artifact_name()
    assert _job().artifact_name() == _job().artifact_name()


def test_artifact_name_unique_per_distinct_job() -> None:
    # Two jobs differing in any single frozen field must produce different artifact names.
    base = _job()
    variants = [
        _job(name="job-2"),
        _job(target="kafka"),
        _job(runner="windows-latest"),
        _job(environment="py3.12"),
        _job(platform="windows"),
        _job(unit_tests=False),
        _job(e2e_tests=True),
    ]
    names = {base.artifact_name()} | {variant.artifact_name() for variant in variants}
    assert len(names) == len(variants) + 1


def test_artifact_name_sanitizes_disallowed_characters() -> None:
    job = _job(name='a/b:c*d?e|f"g<h>i\\j', environment="x\r\ny")
    name = job.artifact_name()
    assert ARTIFACT_NAME_DISALLOWED.search(name) is None
    # Distinct jobs that sanitize to the same readable prefix still differ via the digest.
    other = _job(name="a_b_c_d_e_f_g_h_i_j", environment="x__y")
    assert name != other.artifact_name()


def test_artifact_name_respects_length_cap() -> None:
    job = _job(name="x" * 1000)
    assert len(job.artifact_name()) <= ARTIFACT_NAME_MAX_LENGTH


def test_artifact_name_pure_over_frozen_fields() -> None:
    # Built only from the dataclass fields — reconstructing from asdict reproduces the name.
    job = _job()
    assert BatchJob(**dataclasses.asdict(job)).artifact_name() == job.artifact_name()
