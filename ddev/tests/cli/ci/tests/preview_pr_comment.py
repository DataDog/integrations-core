# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Renders every comment and run-summary scenario to files, for eyeballing the real thing on GitHub.

Unit tests cannot tell you that a ``<details>`` sits wrong inside a ``<blockquote>`` or that the
progress bar wraps on a narrow screen, so the layout has to be looked at at least once per change.

Run it as a module from the ``ddev`` directory — it imports the scenario builders from the renderer's
test module, which only resolves with the ``ddev`` root on ``sys.path``. Running the file by path
puts its own directory there instead, and the import fails::

    cd ddev
    hatch run python -m tests.cli.ci.tests.preview_pr_comment /tmp/dispatcher-preview
    gh pr comment <SCRATCH_PR> --body-file /tmp/dispatcher-preview/02-retrying.md

Not a test: it is named ``preview_`` so pytest does not collect it.
"""

from __future__ import annotations

import sys
from pathlib import Path

from ddev.cli.ci.tests.pr_comment import render_comment, render_run_summary
from ddev.cli.ci.tests.progress import DispatcherProgress, ExecutionState, ProgressError
from ddev.cli.ci.tests.status import Status
from tests.cli.ci.tests.test_pr_comment import attempt, batch, failing_report, job, planned_batch

RUN_URL = "https://github.com/DataDog/integrations-core/actions/runs"


def initial() -> DispatcherProgress:
    return DispatcherProgress(batches=tuple(planned_batch(f"batch-{index:02d}") for index in (1, 2, 3)), done=False)


def retrying() -> DispatcherProgress:
    return DispatcherProgress(
        batches=(
            batch("batch-01", *[job(attempt(), target=f"postgres-{index}") for index in range(4)]),
            batch(
                "batch-02",
                *[job(attempt(), target=f"mysql-{index}") for index in range(4)],
                run_id=122,
                workflow_url=f"{RUN_URL}/122",
            ),
            batch(
                "batch-03",
                job(attempt(Status.FAILURE, reports=(failing_report("test_connection"),)), target="postgres"),
                job(attempt(Status.FAILURE, failed_steps=("Run E2E tests",)), target="redis"),
                *[job(attempt(), target=f"ntp-{index}") for index in range(2)],
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
            batch("batch-01", *[job(attempt(), target=f"postgres-{index}") for index in range(4)]),
            batch(
                "batch-02",
                *[job(attempt(), target=f"mysql-{index}") for index in range(4)],
                run_id=122,
                workflow_url=f"{RUN_URL}/122",
            ),
            batch(
                "batch-03",
                job(attempt(Status.FAILURE), attempt(Status.SUCCESS, number=2), target="postgres"),
                job(attempt(Status.FAILURE), attempt(Status.FAILURE, number=2), target="redis"),
                job(attempt(Status.SKIPPED), target="consul"),
                job(
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
    """A run whose results could not all be established: nothing failed, but it is not a clean pass.

    The ⚠️ heading, alert and unavailable section only appear here, so without this scenario they were
    never looked at on GitHub at all.
    """
    return DispatcherProgress(
        batches=(
            batch("batch-01", *[job(attempt(), target=f"postgres-{index}") for index in range(3)]),
            batch(
                "batch-02",
                job(attempt(error=ProgressError.NO_ARTIFACTS), target="mysql"),
                job(attempt(), target="redis"),
                run_id=122,
                workflow_url=f"{RUN_URL}/122",
            ),
            batch(
                "batch-03",
                job(attempt(), target="consul"),
                error=ProgressError.NO_JOB_RESULTS,
                run_id=123,
                workflow_url=f"{RUN_URL}/123",
            ),
        ),
        done=True,
    )


def main(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    scenarios = (
        ("01-initial", initial()),
        ("02-retrying", retrying()),
        ("03-final", final()),
        ("04-incomplete", incomplete()),
    )
    for name, progress in scenarios:
        path = destination / f"{name}.md"
        path.write_text(render_comment(progress), encoding="utf-8")
        print(f"{path} ({path.stat().st_size} bytes)")

    # The run-summary form of the same report. Rendered from the failing scenario because the note it
    # prepends only shows up when the comment could not be written, which is the case worth seeing.
    summary = destination / "05-run-summary-comment-failed.md"
    summary.write_text(render_run_summary(render_comment(final()), pr_comment_failed=True), encoding="utf-8")
    print(f"{summary} ({summary.stat().st_size} bytes)")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/dispatcher-preview"))
