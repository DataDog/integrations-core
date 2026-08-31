# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Renders every comment scenario to files, for eyeballing the real thing on GitHub.

Unit tests cannot tell you that a ``<details>`` sits wrong inside a ``<blockquote>``. Run as a module
from the ``ddev`` directory, which is what puts the test helpers on ``sys.path``::

    cd ddev
    hatch run python -m tests.cli.ci.tests.preview_pr_comment /tmp/dispatcher-preview

Named ``preview_`` so pytest does not collect it.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

from ddev.cli.ci.tests.pr_comment import (
    render_comment,
    render_compact_comment,
    render_minimal_comment,
    render_run_summary,
)
from ddev.cli.ci.tests.progress import DispatcherProgress, ExecutionState, ProgressError
from ddev.cli.ci.tests.status import Status
from tests.cli.ci.tests.helpers import attempt, batch_progress, failing_report, job_progress, planned_batch

RUN_URL = "https://github.com/DataDog/integrations-core/actions/runs"


def initial() -> DispatcherProgress:
    return DispatcherProgress(batches=tuple(planned_batch(f"batch-{index:02d}") for index in (1, 2, 3)), done=False)


def retrying() -> DispatcherProgress:
    return DispatcherProgress(
        batches=(
            batch_progress("batch-01", *[job_progress(attempt(), target=f"postgres-{index}") for index in range(4)]),
            batch_progress(
                "batch-02",
                *[job_progress(attempt(), target=f"mysql-{index}") for index in range(4)],
                run_id=122,
                workflow_url=f"{RUN_URL}/122",
            ),
            batch_progress(
                "batch-03",
                job_progress(attempt(Status.FAILURE, reports=(failing_report("test_connection"),)), target="postgres"),
                job_progress(attempt(Status.FAILURE, failed_steps=("Run E2E tests",)), target="redis"),
                *[job_progress(attempt(), target=f"ntp-{index}") for index in range(2)],
                state=ExecutionState.RETRYING,
                status=None,
                current_attempt=2,
                max_attempts=3,
                run_id=123,
                workflow_url=f"{RUN_URL}/123",
            ),
        ),
        done=False,
    )


def final() -> DispatcherProgress:
    return DispatcherProgress(
        batches=(
            batch_progress("batch-01", *[job_progress(attempt(), target=f"postgres-{index}") for index in range(4)]),
            batch_progress(
                "batch-02",
                *[job_progress(attempt(), target=f"mysql-{index}") for index in range(4)],
                run_id=122,
                workflow_url=f"{RUN_URL}/122",
            ),
            batch_progress(
                "batch-03",
                job_progress(attempt(Status.FAILURE), attempt(Status.SUCCESS, number=2), target="postgres"),
                job_progress(attempt(Status.FAILURE), attempt(Status.FAILURE, number=2), target="redis"),
                job_progress(attempt(Status.SKIPPED), target="consul"),
                job_progress(
                    attempt(Status.FAILURE, reports=(failing_report("test_connection", "test_timeout"),)),
                    target="vault",
                ),
                status=Status.FAILURE,
                run_id=123,
                current_attempt=2,
                max_attempts=3,
                workflow_url=f"{RUN_URL}/123",
            ),
        ),
        done=True,
    )


def incomplete() -> DispatcherProgress:
    """Nothing failed, but not a clean pass either: the only scenario with the ⚠️ heading and section."""
    return DispatcherProgress(
        batches=(
            batch_progress("batch-01", *[job_progress(attempt(), target=f"postgres-{index}") for index in range(3)]),
            batch_progress(
                "batch-02",
                job_progress(attempt(error=ProgressError.NO_ARTIFACTS), target="mysql"),
                job_progress(attempt(), target="redis"),
                run_id=122,
                workflow_url=f"{RUN_URL}/122",
            ),
            batch_progress(
                "batch-03",
                job_progress(attempt(), target="consul"),
                error=ProgressError.NO_JOB_RESULTS,
                run_id=123,
                workflow_url=f"{RUN_URL}/123",
            ),
        ),
        done=True,
    )


def mixed() -> DispatcherProgress:
    """Failures, an unestablished result and retries at once: the only scenario where all tiers differ.

    Also the case the tier-aware alert exists for — the fallbacks shed the unavailable section, so the
    count has to survive in the alert instead.
    """
    batches = final().batches
    last = batches[-1]
    widened = replace(
        last,
        jobs_progress=(
            *last.jobs_progress,
            job_progress(attempt(error=ProgressError.NO_ARTIFACTS), target="mysql"),
        ),
    )
    return DispatcherProgress(batches=(*batches[:-1], widened), done=True)


def main(destination: Path):
    destination.mkdir(parents=True, exist_ok=True)
    scenarios = (
        ("01-initial", initial()),
        ("02-retrying", retrying()),
        ("03-final", final()),
        ("04-incomplete", incomplete()),
        ("05-mixed", mixed()),
    )
    for name, progress in scenarios:
        path = destination / f"{name}.md"
        path.write_text(render_comment(progress), encoding="utf-8")
        print(f"{path} ({path.stat().st_size} bytes)")

    # The run-summary form, from the failing scenario: the note it prepends only shows up when the
    # comment could not be written.
    summary = destination / "06-run-summary-comment-failed.md"
    summary.write_text(render_run_summary(render_comment(final()), pr_comment_failed=True), encoding="utf-8")
    print(f"{summary} ({summary.stat().st_size} bytes)")

    # The two fallback tiers, never seen in a normal run, from the scenario where they differ most.
    for name, render in (("07-compact", render_compact_comment), ("08-minimal", render_minimal_comment)):
        path = destination / f"{name}.md"
        path.write_text(render(mixed()), encoding="utf-8")
        print(f"{path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/dispatcher-preview"))
