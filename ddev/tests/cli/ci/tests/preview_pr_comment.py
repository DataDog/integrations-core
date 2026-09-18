# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Renders a review set of comment scenarios to files, for eyeballing the real thing on GitHub.

Unit tests cannot tell you that GitHub failed to parse the Markdown inside a `<details>`, or that a
row of links wraps into a wall of brackets on a narrow screen. Every scenario here shows the same
skeleton, so what a reader is comparing between them is the content and not the architecture.

Run as a module from the `ddev` directory, which is what puts the test helpers on `sys.path`:

    cd ddev
    hatch run python -m tests.cli.ci.tests.preview_pr_comment /tmp/dispatcher-preview

Named `preview_pr_comment` rather than `test_` so pytest does not collect it.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from ddev.cli.ci.tests.pr_comment import (
    render_comment,
    render_compact_comment,
    render_shutdown_notice,
    render_truncated_comment,
)
from ddev.cli.ci.tests.progress import DispatcherProgress, ExecutionState, ProgressError
from ddev.cli.ci.tests.status import Status
from ddev.event_bus.shutdown import ShutdownRequest
from ddev.utils.platform import PlatformName
from tests.cli.ci.tests.helpers import attempt, batch_progress, failing_report, job_progress

RUN_URL = "https://github.com/DataDog/integrations-core/actions/runs"


def running_with_failures() -> DispatcherProgress:
    """Failures in a finished batch while the others still report: the mid-run shape."""
    return DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                *[
                    job_progress(
                        attempt(Status.FAILURE, reports=(failing_report("test_connection"),)),
                        target="postgres",
                        environment=f"py3.1{index}",
                    )
                    for index in range(2)
                ],
                job_progress(attempt(Status.FAILURE, failed_steps=("Run E2E tests",)), target="redisdb"),
                job_progress(attempt(), target="ntp"),
                status=Status.FAILURE,
            ),
            batch_progress(
                "batch-02",
                *[job_progress(attempt(), target=f"mysql-{index}") for index in range(3)],
                job_progress(target="vault"),
                state=ExecutionState.RUNNING,
                status=None,
                run_id=122,
                workflow_url=f"{RUN_URL}/122",
            ),
            batch_progress(
                "batch-03",
                job_progress(attempt(), target="consul"),
                state=ExecutionState.ARTIFACT_DOWNLOAD,
                status=None,
                run_id=123,
                workflow_url=f"{RUN_URL}/123",
            ),
        ),
        done=False,
    )


def arbitrary_matrix() -> DispatcherProgress:
    """A finished run whose targets failed overlapping, unequal sets of tests.

    The case that decides whether a reader can still tell which target failed which test: one
    integration where two tests failed everywhere and each target adds something of its own, and
    another where the targets have nothing in common at all.
    """
    common = ("test_metadata_manager", "test_persistent_cache")
    return DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                *[
                    job_progress(
                        attempt(
                            Status.FAILURE,
                            reports=(failing_report(*common, f"test_only_on_py3_1{index}"),),
                            failed_steps=("Run the tests",),
                        ),
                        target="base",
                        environment=f"py3.1{index}",
                        platform=PlatformName.WINDOWS if index % 2 else PlatformName.LINUX,
                        minimum_base_package=index >= 4,
                    )
                    for index in range(6)
                ],
                status=Status.FAILURE,
            ),
            batch_progress(
                "batch-02",
                job_progress(
                    attempt(Status.FAILURE, reports=(failing_report("test_query_timeout"),)),
                    target="sqlserver",
                    environment="py3.13-2019",
                ),
                job_progress(
                    attempt(Status.FAILURE, reports=(failing_report("test_custom_metrics", "test_ao"),)),
                    target="sqlserver",
                    environment="py3.13-2022",
                ),
                job_progress(attempt(Status.FAILURE, failed_steps=("Run the tests", "Upload coverage")), target="kuma"),
                status=Status.FAILURE,
                run_id=122,
                workflow_url=f"{RUN_URL}/122",
            ),
        ),
        done=True,
    )


def nothing_collected() -> DispatcherProgress:
    """Workflows that passed while their reports went missing: incomplete, not failed or clean."""
    return DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                *[job_progress(attempt(), target=f"postgres-{index}") for index in range(3)],
                job_progress(attempt(error=ProgressError.NO_ARTIFACTS), target="mysql"),
                job_progress(attempt(error=ProgressError.NO_ARTIFACTS), target="mysql", environment="py3.13"),
            ),
            batch_progress(
                "batch-02",
                job_progress(attempt(), target="consul"),
                error=ProgressError.NO_JOB_RESULTS,
                run_id=122,
                workflow_url=f"{RUN_URL}/122",
            ),
        ),
        done=True,
    )


def batch_only_failure() -> DispatcherProgress:
    """A workflow that failed outside its integration test jobs: no target to attribute it to."""
    return DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                *[job_progress(attempt(), target=f"postgres-{index}") for index in range(3)],
                status=Status.FAILURE,
            ),
            batch_progress(
                "batch-02",
                job_progress(attempt(Status.FAILURE, reports=(failing_report("test_connection"),)), target="redisdb"),
                status=Status.FAILURE,
                run_id=122,
                workflow_url=f"{RUN_URL}/122",
            ),
        ),
        done=True,
    )


def at_scale() -> DispatcherProgress:
    """More affected targets and test names than any tier can carry in full."""
    jobs = [
        job_progress(
            attempt(
                Status.FAILURE,
                reports=(failing_report(*[f"test_number_{index}" for index in range(20)]),),
                failed_steps=("Run the tests",),
            ),
            target=f"integration-{integration:03d}",
            environment=f"py3.13-{target}",
        )
        for integration in range(120)
        for target in range(8)
    ]
    return DispatcherProgress(
        batches=(
            batch_progress("batch-01", *jobs[: len(jobs) // 2], status=Status.FAILURE),
            batch_progress(
                "batch-02",
                *jobs[len(jobs) // 2 :],
                status=Status.FAILURE,
                run_id=122,
                workflow_url=f"{RUN_URL}/122",
            ),
        ),
        done=True,
    )


def main(destination: Path):
    # Simulate the Dispatcher metadata required by the footer.
    os.environ.setdefault("GITHUB_SERVER_URL", "https://github.com")
    os.environ.setdefault("GITHUB_REPOSITORY", "DataDog/integrations-core")
    os.environ.setdefault("GITHUB_RUN_ID", "12345")
    os.environ.setdefault("GITHUB_SHA", "ff9caa5eb1f0c3d2a4b6")

    destination.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for name, progress in (
        ("01-running-with-failures", running_with_failures()),
        ("02-arbitrary-matrix", arbitrary_matrix()),
        ("03-nothing-collected", nothing_collected()),
        ("04-batch-only-failure", batch_only_failure()),
    ):
        path = destination / f"{name}.md"
        path.write_text(render_comment(progress), encoding="utf-8")
        written.append(path)

    # The three terminal states together, so their wording can be compared at a glance.
    terminal = destination / "05-terminal-states.md"
    terminal.write_text(
        "\n\n---\n\n".join(
            render_comment(running_with_failures(), shutdown=request)
            for request in (
                ShutdownRequest.cancelled(),
                ShutdownRequest.failed(RuntimeError("a batch response failed validation")),
                ShutdownRequest.timed_out(RuntimeError("the run exceeded max_timeout")),
            )
        )
        # A run stopped before any batch reported has no snapshot to render at all.
        + "\n\n---\n\n"
        + render_shutdown_notice(ShutdownRequest.cancelled()),
        encoding="utf-8",
    )
    written.append(terminal)

    # The size fallbacks, from the scenario that reaches them. What they demonstrate is the order the
    # report gives up detail: the test names go, then rows, and a link is the last thing to go.
    fallbacks = at_scale()
    for name, render in (("06-compact", render_compact_comment), ("07-truncated", render_truncated_comment)):
        path = destination / f"{name}.md"
        path.write_text(render(fallbacks), encoding="utf-8")
        written.append(path)

    for path in written:
        print(f"{path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/dispatcher-preview"))
