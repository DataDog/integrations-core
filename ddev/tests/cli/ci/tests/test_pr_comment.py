# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the PR comment renderer.

The first section pins the whole rendered body for each state the comment goes through, because the
layout is specified as exact Markdown and a shape that drifts is the defect. Everything after it
asserts the reporting rules rather than the prose, in the order the report's own priorities put them:
every affected target keeps a linked row of its own, a failed test stays attached to the target that
failed it, and size pressure takes names before it takes links.
"""

from __future__ import annotations

import dataclasses
import re
from collections.abc import Callable

import pytest
from markdown_it import MarkdownIt

from ddev.cli.ci.tests.pr_comment import (
    ALERT_RUNNING_NOTE,
    BATCH_FAILURE_TEXT,
    CANCELLED_HEADING,
    COMMENT_MARKER,
    COMMON_TESTS_LEAD,
    FAILED_HEADING,
    PROGRESS_BAR_ASSETS,
    PROGRESS_BAR_WIDTH,
    SHUTDOWN_ALERTS,
    SHUTDOWN_HEADINGS,
    SHUTDOWN_REASON_LIMIT,
    TIMED_OUT_HEADING,
    render_comment,
    render_compact_comment,
    render_run_summary,
    render_shutdown_notice,
    render_truncated_comment,
    summary_line,
)
from ddev.cli.ci.tests.progress import DispatcherProgress, ExecutionState, ProgressError
from ddev.cli.ci.tests.status import Status
from ddev.event_bus.shutdown import ShutdownKind, ShutdownRequest
from ddev.utils.platform import PlatformName
from tests.cli.ci.tests.helpers import (
    attempt,
    batch_progress,
    failing_report,
    job_progress,
    planned_batch,
    uniform_progress,
)

# GitHub's own ceiling, from the 422 it returns: "body is too long (maximum is 65536 characters)".
# Not imported from the renderer on purpose — a test that reads the same constant it is checking
# would pass no matter what that constant said.
GITHUB_COMMENT_HARD_LIMIT = 65_536

# What the autouse `github_actions_env` fixture makes the footer link to.
DISPATCH_RUN_URL = "https://github.com/DataDog/integrations-core/actions/runs/12345"
# `batch_progress`'s default, which the batch strip links each batch to.
BATCH_RUN_URL = "https://github.com/o/r/actions/runs/121"
# `attempt`'s default, which each affected target's row links to.
TARGET_JOB_URL = "https://github.com/o/r/actions/runs/1/job/9"

# Internal distinctions and mechanical explanations that mean nothing to someone looking at a failing
# pull request. Each one was in the comment at some point; none may come back.
INTERNAL_VOCABULARY = (
    "tracked job",
    "results not established",
    "result not established",
    "the workflow reported no job results",
    "stopped at the time limit",
    "anything below is what had been gathered",
    "were asked to stop",
    "no failure detail",
    "details pending",
    "no artifacts were downloaded",
)


def _progress_bar_of(body: str) -> dict[str, int]:
    """The rendered progress bar, as the pixel width of each segment it drew."""
    return {segment: int(width) for segment, width in re.findall(r'progress-(\w+)\.png" width="(\d+)"', body)}


def _bar(**segments: int) -> str:
    """The bar the renderer draws for these segment widths, as one `<img>` per segment."""
    return "".join(
        f'<img src="{PROGRESS_BAR_ASSETS}/progress-{segment}.png" width="{width}" height="10" alt="">'
        for segment, width in segments.items()
    )


def _batch_strip_of(body: str) -> str:
    """The one line the batch state is rendered onto."""
    return next(line for line in body.splitlines() if line.startswith("Batches · "))


def _group_summaries_of(body: str) -> list[str]:
    """Every affected integration's summary line, in the order the comment lists them."""
    return re.findall(r"<summary>((?:❌|⚠️) <code>.*?</code>: .*?)</summary>", body)


def _target_rows_of(body: str) -> list[str]:
    """Every target row, which is every line opening a top-level bullet."""
    return [line for line in body.splitlines() if line.startswith("- ")]


def _listed_names_of(body: str) -> list[str]:
    """Every name listed beneath a target row, indented under the row it belongs to."""
    return [line.strip().removeprefix("- ").strip("`") for line in body.splitlines() if line.startswith("  - ")]


def shutdown_request(kind: ShutdownKind) -> ShutdownRequest:
    """A representative request for *kind*, for the tests that render a stopped run."""
    if kind is ShutdownKind.CANCELLED:
        return ShutdownRequest.cancelled()
    if kind is ShutdownKind.FAILED:
        return ShutdownRequest.failed(RuntimeError("a fatal error"))
    return ShutdownRequest.timed_out(RuntimeError("a fatal error"))


@pytest.fixture
def on_a_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    """The commit a finished run's footer names, which the shared env fixture leaves unset."""
    monkeypatch.setenv("GITHUB_SHA", "ff9caa5eb1f0c3d2a4b6")


# ---------------------------------------------------------------------------
# The whole body, per state
#
# The layout is specified as exact Markdown, down to the blank line after every `</summary>` that
# GitHub needs in order to parse the disclosure's contents at all. Substring assertions cannot catch
# a lost blank line or a block that moved, so these pin the body and the rest of the file does not.
# ---------------------------------------------------------------------------


def test_a_queued_run_renders_the_plan_and_nothing_else():
    """Nothing has run, so the comment is the plan: no links yet, and no failure section."""
    progress = DispatcherProgress(
        batches=(planned_batch("batch-01", job_count=3), planned_batch("batch-02", job_count=2)),
        done=False,
    )

    assert render_comment(progress) == (
        f"""{COMMENT_MARKER}

## 🔄 Dispatcher tests: in progress

> **Dispatcher beta: informational only**
> Existing CI remains the merge signal.

> [!NOTE]
> **Tests are still running.** 2 of 2 batches have not finished yet. 5 of 5 jobs have not reported. \
This comment updates automatically.

{_bar(pending=240)}&nbsp; **0/5 jobs**

⏳ 5 pending

Batches · ⏳ `batch-01` 0/3 · ⏳ `batch-02` 0/2 — *links available after dispatch*

<sub>⏳ Dispatcher running — [GitHub Run]({DISPATCH_RUN_URL}).</sub>"""
    )


def test_a_running_run_reports_the_failures_it_already_has():
    """Two integrations have failed in a finished batch while two batches are still reporting."""
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                *_ddev_targets(),
                *_checkpoint_targets(),
                status=Status.FAILURE,
            ),
            batch_progress(
                "batch-02",
                job_progress(attempt(), target="vault"),
                job_progress(target="consul"),
                state=ExecutionState.RUNNING,
                status=None,
            ),
            batch_progress(
                "batch-03",
                job_progress(attempt(), target="nginx"),
                state=ExecutionState.ARTIFACT_DOWNLOAD,
                status=None,
            ),
        ),
        done=False,
    )

    assert render_comment(progress) == (
        f"""{COMMENT_MARKER}

## 🔄 Dispatcher tests: in progress

> **Dispatcher beta: informational only**
> Existing CI remains the merge signal.

> [!NOTE]
> **Tests are still running.** 2 of 3 batches have not finished yet. 1 of 7 jobs have not reported. \
This comment updates automatically.

{_bar(passed=69, failed=137, pending=34)}&nbsp; **6/7 jobs**

✅ 2 passed · ❌ 4 failed · ⏳ 1 pending

Batches · ❌ [batch-01]({BATCH_RUN_URL}) 4/4 · 🔄 [batch-02]({BATCH_RUN_URL}) 1/2 · \
📥 [batch-03]({BATCH_RUN_URL}) 1/1

<details>
<summary>❌ <code>checkpoint_harmony_endpoint</code>: 2 failed targets</summary>

- [`py3.13 / linux`]({TARGET_JOB_URL}) · batch-01 · step `Run the tests`
- [`py3.13 / linux / minimum base package`]({TARGET_JOB_URL}) · batch-01 · step `Run the tests`

</details>

<details>
<summary>❌ <code>ddev</code>: 2 failed targets</summary>

- [`default / linux`]({TARGET_JOB_URL}) · batch-01
- [`default / windows`]({TARGET_JOB_URL}) · batch-01

Tests failed in every target:
- `tests.test_check::test_dispatch_tests_plans_from_hatch_toml`

</details>

<sub>⏳ Dispatcher running — [GitHub Run]({DISPATCH_RUN_URL}).</sub>"""
    )


def test_a_failed_run_groups_every_kind_of_bad_news_by_integration(on_a_commit):
    """Failed tests, a failed step, missing artifacts alongside a failure, and a lone missing result.

    One group per integration regardless of which of those it is, because the reader's question is
    about the integration and not about which of the four shapes its answer happens to take. Each
    target keeps its own row and its own link whichever shape it is in.
    """
    progress = DispatcherProgress(
        batches=(
            batch_progress("batch-01", *_ddev_targets(), *_checkpoint_targets(), status=Status.FAILURE),
            batch_progress("batch-02", *_kafka_targets(), _kuma_target(), status=Status.FAILURE),
            batch_progress(
                "batch-03",
                job_progress(
                    attempt(Status.FAILURE, reports=(failing_report("test_pg_stat_statements_dealloc_v2"),)),
                    target="postgres",
                    environment="py3.13-18.0-C",
                ),
                job_progress(attempt(), target="mysql"),
                status=Status.FAILURE,
            ),
            batch_progress(
                "batch-04",
                job_progress(attempt(), target="redisdb"),
                job_progress(attempt(), target="zk"),
            ),
        ),
        done=True,
    )

    assert render_comment(progress) == (
        f"""{COMMENT_MARKER}

## ❌ Dispatcher tests: failed

> **Dispatcher beta: informational only**
> Existing CI remains the merge signal.

> [!CAUTION]
> **4 integrations failed.** 7 of 11 jobs failed. Dispatcher could not collect test results for 3 targets.

{_bar(passed=87, failed=153)}&nbsp; **11/11 jobs**

✅ 4 passed · ❌ 7 failed

Batches · ❌ [batch-01]({BATCH_RUN_URL}) 4/4 · ❌ [batch-02]({BATCH_RUN_URL}) 3/3 · \
❌ [batch-03]({BATCH_RUN_URL}) 2/2 · ✅ [batch-04]({BATCH_RUN_URL}) 2/2

<details>
<summary>❌ <code>checkpoint_harmony_endpoint</code>: 2 failed targets</summary>

- [`py3.13 / linux`]({TARGET_JOB_URL}) · batch-01 · step `Run the tests`
- [`py3.13 / linux / minimum base package`]({TARGET_JOB_URL}) · batch-01 · step `Run the tests`

</details>

<details>
<summary>❌ <code>ddev</code>: 2 failed targets</summary>

- [`default / linux`]({TARGET_JOB_URL}) · batch-01
- [`default / windows`]({TARGET_JOB_URL}) · batch-01

Tests failed in every target:
- `tests.test_check::test_dispatch_tests_plans_from_hatch_toml`

</details>

<details>
<summary>❌ <code>kafka_actions</code>: 2 failed targets</summary>

- [`py3.12 / linux`]({TARGET_JOB_URL}) · batch-02 · step `Run ./.github/actions/setup-ddev` · \
artifacts could not be downloaded
- [`py3.12 / linux / minimum base package`]({TARGET_JOB_URL}) · batch-02 · \
step `Run ./.github/actions/setup-ddev` · artifacts could not be downloaded

</details>

<details>
<summary>❌ <code>postgres</code>: 1 failed target</summary>

- [`py3.13-18.0-C / linux`]({TARGET_JOB_URL}) · batch-03 · test `tests.test_check::test_pg_stat_statements_dealloc_v2`

</details>

<details>
<summary>⚠️ <code>kuma</code>: result unavailable for 1 target</summary>

- [`py3.13-2.10.6 / linux`]({TARGET_JOB_URL}) · batch-02 · artifacts could not be downloaded

</details>

<sub>Dispatcher finished on `ff9caa5` — [GitHub Run]({DISPATCH_RUN_URL}).</sub>"""
    )


def test_a_clean_run_collapses_to_the_batch_strip(on_a_commit):
    """Nothing failed, so there is nothing to disclose: the totals and the batches are the report."""
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                job_progress(attempt(), target="redisdb"),
                job_progress(attempt(), target="nginx"),
                job_progress(attempt(), target="vault"),
            ),
            batch_progress(
                "batch-02",
                job_progress(attempt(), target="consul"),
                job_progress(attempt(), target="zk"),
            ),
        ),
        done=True,
    )

    assert render_comment(progress) == (
        f"""{COMMENT_MARKER}

## ✅ Dispatcher tests: passed

> **Dispatcher beta: informational only**
> Existing CI remains the merge signal.

{_bar(passed=240)}&nbsp; **5/5 jobs**

✅ 5 passed · nothing failed

Batches · ✅ [batch-01]({BATCH_RUN_URL}) 3/3 · ✅ [batch-02]({BATCH_RUN_URL}) 2/2

<sub>Dispatcher finished on `ff9caa5` — [GitHub Run]({DISPATCH_RUN_URL}).</sub>"""
    )


def _ddev_targets() -> list:
    """Two targets of one integration failing the same single test, on two platforms."""
    return [
        job_progress(
            attempt(
                Status.FAILURE,
                reports=(failing_report("test_dispatch_tests_plans_from_hatch_toml"),),
                failed_steps=("Run the tests",),
            ),
            target="ddev",
            environment="default",
            platform=platform,
        )
        for platform in (PlatformName.LINUX, PlatformName.WINDOWS)
    ]


def _checkpoint_targets() -> list:
    """Two targets failing a step, with no test-level detail: an ordinary job and its replica."""
    return [
        job_progress(
            attempt(Status.FAILURE, failed_steps=("Run the tests",)),
            target="checkpoint_harmony_endpoint",
            environment="py3.13",
            minimum_base_package=minimum,
        )
        for minimum in (False, True)
    ]


def _kafka_targets() -> list:
    """Two targets that failed in setup, so their artifacts never arrived either."""
    return [
        job_progress(
            attempt(
                Status.FAILURE,
                failed_steps=("Run ./.github/actions/setup-ddev",),
                error=ProgressError.NO_ARTIFACTS,
            ),
            target="kafka_actions",
            environment="py3.12",
            minimum_base_package=minimum,
        )
        for minimum in (False, True)
    ]


def _kuma_target():
    """A target that concluded successfully but whose artifacts never arrived: result unknown."""
    return job_progress(attempt(error=ProgressError.NO_ARTIFACTS), target="kuma", environment="py3.13-2.10.6")


# ---------------------------------------------------------------------------
# One structure, whatever the state
# ---------------------------------------------------------------------------

SECTION_MARKERS = (
    COMMENT_MARKER,
    "## ",
    "> **Dispatcher beta",
    "&nbsp; **",
    "Batches · ",
    "<sub>",
)


@pytest.mark.parametrize(
    ("name", "progress"),
    [
        ("queued", DispatcherProgress(batches=(planned_batch("batch-01"),), done=False)),
        ("running", uniform_progress(complete=4)),
        ("passed", uniform_progress(done=True)),
        (
            "failed",
            DispatcherProgress(
                batches=(batch_progress("batch-01", *_ddev_targets(), status=Status.FAILURE),),
                done=True,
            ),
        ),
        (
            "incomplete",
            DispatcherProgress(
                batches=(batch_progress("batch-01", _kuma_target()),),
                done=True,
            ),
        ),
    ],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_every_state_puts_its_sections_in_the_same_order(name: str, progress: DispatcherProgress):
    """A queued run and a failed one differ in what they say, never in where they say it.

    The bug this rules out is an information architecture per state: a reader who has learnt where
    the batch links live should not have to find them again because the run finished.
    """
    body = render_comment(progress)

    positions = [body.index(marker) for marker in SECTION_MARKERS]
    assert positions == sorted(positions), body
    # Affected integrations sit between the batch strip and the footer, never above the totals.
    if "<details>" in body:
        assert body.index("Batches · ") < body.index("<details>") < body.index("<sub>")


# ---------------------------------------------------------------------------
# Target rows: one per affected target, each with its own job link
# ---------------------------------------------------------------------------


def _same_test_targets(count: int, *, target: str = "base", batch_id: str = "batch-01"):
    """A group of *count* targets, each failing a test of its own so nothing factors out."""
    return batch_progress(
        batch_id,
        *[
            job_progress(
                attempt(Status.FAILURE, reports=(failing_report(f"test_{index}"),)),
                target=target,
                environment=f"py3.1{index}",
            )
            for index in range(count)
        ],
        status=Status.FAILURE,
    )


@pytest.mark.parametrize("targets", [1, 2, 4, 5, 12, 30])
def test_every_affected_target_keeps_its_own_row_and_job_link(targets: int):
    """The job link is what a reader came for, so no count is a reason to stop rendering one.

    A group that folded its targets onto a shared line at some threshold left the targets past it
    with no way into the run that failed, which is the one thing the comment exists to provide.
    """
    progress = DispatcherProgress(batches=(_same_test_targets(targets),), done=True)

    body = render_comment(progress)

    rows = _target_rows_of(body)
    assert len(rows) == targets
    assert all(TARGET_JOB_URL in row for row in rows)
    assert f"{targets} failed target" in body


def test_a_group_does_not_change_shape_when_it_gains_a_target():
    """Four targets and five targets are the same report with one more row.

    The renderer used to compress a group's targets onto one line at the fifth, so this is the exact
    boundary where the shape used to change for a reason that had nothing to do with size.
    """

    def group_of(targets: int) -> list[str]:
        body = render_comment(DispatcherProgress(batches=(_same_test_targets(targets),), done=True))
        return body.split("<details>")[1].split("</details>")[0].splitlines()

    four, five = group_of(4), group_of(5)

    assert _target_rows_of("\n".join(four)) == _target_rows_of("\n".join(five))[:4]
    # Same skeleton, one row longer: no line of it says anything different about its shape.
    assert [line for line in four if not line.startswith("- ")] == [
        line.replace("5 failed targets", "4 failed targets") for line in five if not line.startswith("- ")
    ]


def test_a_group_spanning_batches_names_the_batch_on_every_row():
    """An integration's targets are partitioned across batches, so the row says which one to open."""
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                job_progress(attempt(Status.FAILURE, failed_steps=("Run the tests",)), target="base"),
                status=Status.FAILURE,
            ),
            batch_progress(
                "batch-02",
                job_progress(
                    attempt(Status.FAILURE, failed_steps=("Run the tests",)),
                    target="base",
                    environment="py3.11",
                ),
                status=Status.FAILURE,
            ),
        ),
        done=True,
    )

    rows = _target_rows_of(render_comment(progress))

    assert len(rows) == 2
    assert "batch-01" in rows[0]
    assert "batch-02" in rows[1]


def test_a_target_without_a_job_url_is_still_named():
    """A job GitHub never reported has no link, and the row is what says the target was affected."""
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                job_progress(attempt(Status.FAILURE, job_url=None), target="base", environment="py3.13"),
                status=Status.FAILURE,
            ),
        ),
        done=True,
    )

    body = render_comment(progress)

    assert "- `py3.13 / linux` · batch-01" in body
    assert "](None)" not in body


def test_a_target_with_no_environment_is_not_labelled_with_a_stray_separator():
    """A target that defines no environments has an empty `BatchJob.environment`."""
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                job_progress(attempt(Status.FAILURE), target="base", environment=""),
                status=Status.FAILURE,
            ),
        ),
        done=True,
    )

    body = render_comment(progress)

    assert "[`linux`]" in body
    assert "[` / linux`]" not in body


def test_a_replica_is_distinguishable_from_its_ordinary_job():
    """The minimum-base-package replica shares its environment and platform with the ordinary job."""
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                *[
                    job_progress(
                        attempt(Status.FAILURE),
                        target="base",
                        environment="py3.13",
                        minimum_base_package=minimum,
                    )
                    for minimum in (False, True)
                ],
                status=Status.FAILURE,
            ),
        ),
        done=True,
    )

    rows = _target_rows_of(render_comment(progress))

    assert len(set(rows)) == 2
    assert any("minimum base package" in row for row in rows)


# ---------------------------------------------------------------------------
# A failed test belongs to the target that failed it
# ---------------------------------------------------------------------------


def _matrix(*per_target: tuple[str, ...], target: str = "base") -> DispatcherProgress:
    """One integration whose targets failed the test sets given, in order."""
    return DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                *[
                    job_progress(
                        attempt(Status.FAILURE, reports=(failing_report(*tests),)),
                        target=target,
                        environment=f"py3.1{index}",
                    )
                    for index, tests in enumerate(per_target)
                ],
                status=Status.FAILURE,
            ),
        ),
        done=True,
    )


def test_overlapping_test_sets_stay_with_the_target_that_failed_them():
    """The union of a group's failures says which tests broke and nothing about where.

    Target A failed `test_x` and `test_y`; target B failed `test_y` and `test_z`. A flat list of
    three names under the group would be true of the group and false of both of its targets, so
    `test_x` and `test_z` stay on the rows that reported them and only `test_y` is said once.
    """
    body = render_comment(_matrix(("test_x", "test_y"), ("test_y", "test_z")))

    rows, common = body.split(COMMON_TESTS_LEAD)
    first, second = rows.split("\n- [")[1:]
    assert _listed_names_of(first) == ["tests.test_check::test_x"]
    assert _listed_names_of(second) == ["tests.test_check::test_z"]
    assert _listed_names_of(common) == []
    assert common.count("test_y") == 1


def test_tests_that_failed_in_every_target_are_listed_once_and_the_rest_are_additional():
    """The one group-level list, and it is lossless.

    Target A failed `test_a`, `test_b`, `test_c`; target B failed `test_a` and `test_c`. So the
    common pair goes below the rows and A keeps `test_b` as an additional failure — from which either
    target's full set can be read back.
    """
    body = render_comment(_matrix(("test_a", "test_b", "test_c"), ("test_a", "test_c")))

    assert COMMON_TESTS_LEAD in body
    common = body.split(COMMON_TESTS_LEAD)[1]
    assert "tests.test_check::test_a" in common
    assert "tests.test_check::test_c" in common
    # Named once for the group, so a target's own list must not repeat it.
    rows = body.split(COMMON_TESTS_LEAD)[0]
    assert "1 additional failed test" in rows
    assert _listed_names_of(rows) == ["tests.test_check::test_b"]


def test_targets_with_nothing_in_common_each_keep_their_own_tests():
    """An empty intersection means there is nothing to factor out, so no list appears above them."""
    body = render_comment(_matrix(("test_x", "test_y"), ("test_z",)))

    assert COMMON_TESTS_LEAD not in body
    assert "additional" not in body
    first, second = body.split("\n- [")[1:]
    assert _listed_names_of(first) == ["tests.test_check::test_x", "tests.test_check::test_y"]
    assert "test `tests.test_check::test_z`" in second


def test_a_test_shared_by_only_some_targets_is_not_factored_out():
    """A claim about every target must be true of every target.

    Three targets, and `test_y` failed in only two of them. Listing it as common would tell a reader
    the third target failed a test it passed.
    """
    body = render_comment(_matrix(("test_x", "test_y"), ("test_y",), ("test_z",)))

    assert COMMON_TESTS_LEAD not in body
    assert "additional" not in body
    assert sorted(_listed_names_of(body)) == [
        "tests.test_check::test_x",
        "tests.test_check::test_y",
    ]


@pytest.mark.parametrize(
    "unestablished",
    [
        pytest.param(attempt(Status.FAILURE, error=ProgressError.NO_ARTIFACTS), id="artifacts-missing"),
        pytest.param(attempt(Status.FAILURE, failed_steps=("Run the tests",)), id="step-only"),
        pytest.param(attempt(error=ProgressError.NO_ARTIFACTS), id="results-never-arrived"),
    ],
)
def test_no_common_claim_is_made_when_a_target_has_no_established_reports(unestablished):
    """A target with no test list of its own cannot support a claim about all of them.

    Two targets failed the same test and a third has no report to intersect, so the group keeps every
    test where it can be believed: under the target that reported it.
    """
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                job_progress(
                    attempt(Status.FAILURE, reports=(failing_report("test_a"),)),
                    target="base",
                    environment="py3.13",
                ),
                job_progress(
                    attempt(Status.FAILURE, reports=(failing_report("test_a"),)),
                    target="base",
                    environment="py3.12",
                ),
                job_progress(unestablished, target="base", environment="py3.11"),
                status=Status.FAILURE,
            ),
        ),
        done=True,
    )

    body = render_comment(progress)

    assert COMMON_TESTS_LEAD not in body
    assert body.count("test `tests.test_check::test_a`") == 2


def test_a_lone_target_keeps_its_tests_under_itself():
    """One target has nothing to share with, so "every target" would be a claim about one."""
    body = render_comment(_matrix(("test_a", "test_b")))

    assert COMMON_TESTS_LEAD not in body
    assert "2 failed tests" in body
    assert _listed_names_of(body) == ["tests.test_check::test_a", "tests.test_check::test_b"]


def test_a_target_failing_several_steps_names_them_under_itself():
    """Steps are never factored out, so each target's own list is the only place they appear."""
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                job_progress(
                    attempt(Status.FAILURE, failed_steps=("Run the tests", "Upload the job's reports")),
                    target="base",
                ),
                status=Status.FAILURE,
            ),
        ),
        done=True,
    )

    body = render_comment(progress)

    assert "2 failed steps" in body
    assert _listed_names_of(body) == ["Run the tests", "Upload the job's reports"]


def test_steps_are_not_named_when_tests_already_explain_the_target():
    """The step that ran a failing test says nothing the test does not."""
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                job_progress(
                    attempt(
                        Status.FAILURE,
                        reports=(failing_report("test_a"),),
                        failed_steps=("Run the tests",),
                    ),
                    target="base",
                ),
                status=Status.FAILURE,
            ),
        ),
        done=True,
    )

    body = render_comment(progress)

    assert "test `tests.test_check::test_a`" in body
    assert "Run the tests" not in body


def test_a_collection_error_is_reported_once_against_its_own_target():
    """One underlying problem, one user-facing explanation, next to the link it applies to.

    The group used to repeat the reason below all of its rows as well, which left a reader matching
    a detached warning against a list of targets to work out which of them it was about.
    """
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                job_progress(attempt(error=ProgressError.NO_ARTIFACTS), target="base", environment="py3.13"),
                job_progress(attempt(), target="base", environment="py3.12"),
                status=Status.SUCCESS,
            ),
        ),
        done=True,
    )

    body = render_comment(progress)

    assert body.count("artifacts could not be downloaded") == 1
    row = next(line for line in _target_rows_of(body) if "py3.13" in line)
    assert row.endswith("artifacts could not be downloaded")


# ---------------------------------------------------------------------------
# What a group's summary claims
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("attempts", "expected"),
    [
        pytest.param(
            (attempt(Status.FAILURE), attempt(Status.FAILURE)),
            "❌ <code>base</code>: 2 failed targets",
            id="failures",
        ),
        pytest.param(
            (attempt(error=ProgressError.NO_ARTIFACTS), attempt(error=ProgressError.NO_ARTIFACTS)),
            "⚠️ <code>base</code>: results unavailable for 2 targets",
            id="nothing-collected",
        ),
        pytest.param(
            (attempt(Status.FAILURE), attempt(error=ProgressError.NO_ARTIFACTS)),
            "❌ <code>base</code>: 1 failed target, 1 result unavailable",
            id="mixed",
        ),
        pytest.param(
            (attempt(Status.FAILURE, error=ProgressError.NO_ARTIFACTS),),
            "❌ <code>base</code>: 1 failed target",
            id="failed-and-lost-its-reports",
        ),
    ],
)
def test_a_group_counts_its_outcomes_in_the_unit_each_one_is_in(attempts, expected: str):
    """A failure and a missing result are different facts, so one number cannot carry both.

    The summary used to count tests, which said nothing about how many targets were broken and put a
    number nobody navigates by where the outcome belongs.
    """
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                *[job_progress(one, target="base", environment=f"py3.1{index}") for index, one in enumerate(attempts)],
                status=Status.FAILURE,
            ),
        ),
        done=True,
    )

    assert _group_summaries_of(render_comment(progress)) == [expected]


def test_groups_are_ordered_by_how_many_targets_they_lost():
    """Worst first, so the integration a reader is most likely to own is at the top."""
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                job_progress(attempt(Status.FAILURE), target="one"),
                *[
                    job_progress(attempt(Status.FAILURE), target="three", environment=f"py3.1{index}")
                    for index in range(3)
                ],
                *[
                    job_progress(attempt(Status.FAILURE), target="two", environment=f"py3.1{index}")
                    for index in range(2)
                ],
                status=Status.FAILURE,
            ),
        ),
        done=True,
    )

    summaries = _group_summaries_of(render_comment(progress))

    assert [summary.split("<code>")[1].split("</code>")[0] for summary in summaries] == ["three", "two", "one"]


def test_a_group_with_only_missing_results_is_a_warning_not_a_failure():
    """Nothing here failed. Calling it a failure claims the integration is broken on no evidence."""
    progress = DispatcherProgress(batches=(batch_progress("batch-01", _kuma_target()),), done=True)

    summaries = _group_summaries_of(render_comment(progress))

    assert summaries == ["⚠️ <code>kuma</code>: result unavailable for 1 target"]


def test_a_real_failure_is_not_displaced_by_groups_with_only_missing_results():
    """A warning-only group with more targets must not outrank the one actionable failure.

    Ordering decides which rows a truncated report keeps, so a group nobody can act on sorting above
    a real failure is how the one thing worth reading gets dropped.
    """
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                *[
                    job_progress(attempt(error=ProgressError.NO_ARTIFACTS), target="wide", environment=f"py3.1{index}")
                    for index in range(6)
                ],
                job_progress(attempt(Status.FAILURE), target="narrow"),
                status=Status.FAILURE,
            ),
        ),
        done=True,
    )

    summaries = _group_summaries_of(render_comment(progress))

    assert summaries[0].startswith("❌ <code>narrow</code>")


# ---------------------------------------------------------------------------
# Problems that belong to a batch rather than to an integration
# ---------------------------------------------------------------------------


def test_a_batch_only_failure_is_linked_and_says_what_happened():
    """A workflow can fail in a step no target's job covers, leaving nothing to group."""
    progress = DispatcherProgress(
        batches=(batch_progress("batch-01", job_progress(attempt(), target="redisdb"), status=Status.FAILURE),),
        done=True,
    )

    body = render_comment(progress)

    assert f"❌ [`batch-01`]({BATCH_RUN_URL}): {BATCH_FAILURE_TEXT}" in body
    assert "<details>" not in body


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        pytest.param(ProgressError.TIMED_OUT, "timed out", id="timed-out"),
        pytest.param(ProgressError.NO_JOB_RESULTS, "test results could not be collected", id="no-job-results"),
        pytest.param(ProgressError.NO_ARTIFACTS, "artifacts could not be downloaded", id="no-artifacts"),
    ],
)
def test_a_batch_problem_no_target_explains_is_reported_against_the_batch(error: ProgressError, expected: str):
    """The batch is the only unit the problem is in, so the note links the batch."""
    progress = DispatcherProgress(
        batches=(batch_progress("batch-01", job_progress(attempt(), target="redisdb"), error=error),),
        done=True,
    )

    body = render_comment(progress)

    assert f"⚠️ [`batch-01`]({BATCH_RUN_URL}): {expected}" in body
    assert "passed" not in _group_summaries_of(body)


def test_a_batch_problem_its_own_targets_already_explain_is_not_said_twice():
    """One problem, one explanation, in the unit the reader can navigate by.

    A batch that lost its artifacts and a target that lost its artifacts are the same event seen at
    two levels. The target's row carries a job link, so that is the one that survives.
    """
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                job_progress(attempt(error=ProgressError.NO_ARTIFACTS), target="mysql"),
                error=ProgressError.NO_ARTIFACTS,
            ),
        ),
        done=True,
    )

    body = render_comment(progress)

    assert body.count("artifacts could not be downloaded") == 1
    assert "[`batch-01`]" not in body


def test_batch_status_is_the_workflow_not_a_roll_up_of_its_jobs():
    """A batch can fail while every job inside it passed, and the strip must not hide that."""
    progress = DispatcherProgress(
        batches=(batch_progress("batch-01", job_progress(attempt(), target="redisdb"), status=Status.FAILURE),),
        done=True,
    )

    assert _batch_strip_of(render_comment(progress)).startswith(f"Batches · ❌ [batch-01]({BATCH_RUN_URL}) 1/1")


def test_a_finished_batch_with_no_status_says_so_rather_than_guessing():
    """A finished batch has a `None` `status` only if something went wrong upstream."""
    progress = DispatcherProgress(
        batches=(batch_progress("batch-01", job_progress(attempt(), target="redisdb"), status=None),),
        done=True,
    )

    assert "❔ [batch-01]" in _batch_strip_of(render_comment(progress))


@pytest.mark.parametrize("job_finished", [False, True], ids=["awaiting-job-status", "job-passed"])
def test_workflow_only_failure_requires_observed_job_outcomes(job_finished: bool):
    """Before its jobs report, a failed batch may still have a failing job to attribute it to."""
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                job_progress(*((attempt(),) if job_finished else ()), target="redisdb"),
                status=Status.FAILURE,
            ),
        ),
        done=True,
    )

    assert (BATCH_FAILURE_TEXT in render_comment(progress)) is job_finished


@pytest.mark.parametrize("state", [ExecutionState.RUNNING, ExecutionState.RETRYING])
def test_a_running_batch_and_a_retrying_batch_are_indistinguishable(state: ExecutionState):
    """A rerun is Dispatcher's own business; at the batch level it is unfinished work."""
    progress = DispatcherProgress(
        batches=(batch_progress("batch-01", job_progress(attempt(), target="redisdb"), state=state, status=None),),
        done=False,
    )

    assert "🔄 [batch-01]" in _batch_strip_of(render_comment(progress))


def test_a_collecting_batch_reads_as_collecting_whatever_its_status_is():
    """Artifact collection outlives the workflow's own conclusion."""
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                job_progress(attempt(), target="redisdb"),
                state=ExecutionState.ARTIFACT_DOWNLOAD,
                status=Status.SUCCESS,
            ),
        ),
        done=False,
    )

    body = render_comment(progress)

    assert "📥 [batch-01]" in _batch_strip_of(body)
    assert "**Tests finished; collecting results.**" in body


# ---------------------------------------------------------------------------
# The heading and the alert
# ---------------------------------------------------------------------------


def test_the_failure_alert_is_counted_in_the_unit_the_failures_are_grouped_into():
    """Integrations, because that is what the body below is grouped into."""
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                *_ddev_targets(),
                job_progress(attempt(Status.FAILURE), target="nginx"),
                status=Status.FAILURE,
            ),
        ),
        done=True,
    )

    body = render_comment(progress)

    assert "> **2 integrations failed.** 3 of 3 jobs failed." in body
    assert len(_group_summaries_of(body)) == 2


def test_one_failing_integration_is_said_in_the_singular():
    progress = DispatcherProgress(
        batches=(batch_progress("batch-01", *_ddev_targets(), status=Status.FAILURE),),
        done=True,
    )

    assert "> **1 integration failed.** 2 of 2 jobs failed." in render_comment(progress)


def test_a_failure_with_no_integration_behind_it_still_announces_itself():
    """A batch's workflow failed with nothing inside it failing: no integration to count."""
    progress = DispatcherProgress(
        batches=(batch_progress("batch-01", job_progress(attempt(), target="redisdb"), status=Status.FAILURE),),
        done=True,
    )

    body = render_comment(progress)

    assert "> **Dispatcher tests failed.** See the failures below." in body
    assert "integrations failed" not in body
    assert "of 1 jobs failed" not in body


def test_collection_failures_are_counted_apart_from_the_jobs_that_failed():
    """Targets and batches are different units, so they get a sentence each and are never summed."""
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                job_progress(attempt(Status.FAILURE), target="nginx"),
                job_progress(attempt(error=ProgressError.NO_ARTIFACTS), target="kuma"),
                status=Status.FAILURE,
            ),
            batch_progress(
                "batch-02",
                job_progress(attempt(), target="redisdb"),
                error=ProgressError.NO_JOB_RESULTS,
            ),
        ),
        done=True,
    )

    body = render_comment(progress)

    assert "Dispatcher could not collect test results for 1 target." in body
    assert "Dispatcher could not collect results for 1 batch." in body
    assert "2 results" not in body


def test_a_workflow_that_passed_without_its_reports_reads_as_incomplete():
    """Neither failed nor a clean pass: the reports never arrived, so nothing is known."""
    progress = DispatcherProgress(batches=(batch_progress("batch-01", _kuma_target()),), done=True)

    body = render_comment(progress)

    assert "## ⚠️ Dispatcher tests: results incomplete" in body
    assert "> [!WARNING]\n> **Results are incomplete.**" in body
    assert "[!CAUTION]" not in body
    assert "nothing failed" not in body


def test_a_finished_run_says_nothing_failed_only_when_that_is_the_whole_truth():
    """Alongside results that never arrived, "nothing failed" is what a reader would remember."""
    clean = render_comment(uniform_progress(done=True))
    incomplete = render_comment(
        DispatcherProgress(
            batches=(batch_progress("batch-01", job_progress(attempt(), target="ntp"), _kuma_target()),),
            done=True,
        )
    )

    assert "nothing failed" in clean
    assert "nothing failed" not in incomplete


def test_a_real_failure_outranks_a_missing_result():
    """A run with both is a failed run: the heading reports the worse of the two."""
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                job_progress(attempt(Status.FAILURE), target="nginx"),
                _kuma_target(),
                status=Status.FAILURE,
            ),
        ),
        done=True,
    )

    assert "## ❌ Dispatcher tests: failed" in render_comment(progress)


def test_a_missing_result_is_not_counted_as_a_failed_integration():
    """The group renders as a warning, so counting it as a failure would contradict the body."""
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                job_progress(attempt(Status.FAILURE), target="nginx"),
                _kuma_target(),
                status=Status.FAILURE,
            ),
        ),
        done=True,
    )

    body = render_comment(progress)

    assert "> **1 integration failed.**" in body
    assert len(_group_summaries_of(body)) == 2


def test_an_unfinished_run_is_unmistakable():
    """A snapshot mid-run must never read as a final verdict."""
    body = render_comment(uniform_progress(complete=4))

    assert "## 🔄 Dispatcher tests: in progress" in body
    assert "> [!NOTE]\n> **Tests are still running.**" in body
    assert ALERT_RUNNING_NOTE in body


def test_a_retrying_run_with_every_job_reported_still_reads_as_unfinished():
    """A retrying batch has every job reported while the batch runs on."""
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                job_progress(attempt(Status.FAILURE), target="nginx"),
                state=ExecutionState.RETRYING,
                status=None,
            ),
        ),
        done=False,
    )

    body = render_comment(progress)

    assert "## 🔄 Dispatcher tests: in progress" in body
    assert "1 of 1 batch has not finished yet." in body
    # A full bar next to an in-progress heading would contradict it.
    assert _progress_bar_of(body)["pending"] > 0


@pytest.mark.parametrize("done", [False, True])
def test_progress_signals_agree_with_each_other(done: bool):
    """The heading, the alert, the footer and the bar all describe the same snapshot."""
    body = render_comment(uniform_progress(done=done, complete=10 if done else 4))

    running = "in progress" in body
    assert running is not done
    assert ("⏳ Dispatcher running" in body) is not done
    assert ("[!NOTE]" in body) is not done


# ---------------------------------------------------------------------------
# Totals and the bar
# ---------------------------------------------------------------------------


def test_a_zero_is_left_out_of_the_totals_rather_than_printed():
    body = render_comment(uniform_progress(complete=0))

    assert "⏳ 10 pending" in body
    assert "0 passed" not in body
    assert "0 failed" not in body


def test_skipped_is_shown_only_when_non_zero():
    progress = DispatcherProgress(
        batches=(batch_progress("batch-01", job_progress(attempt(Status.SKIPPED), target="ntp")),),
        done=True,
    )

    assert "⏭️ 1 skipped" in render_comment(progress)
    assert "skipped" not in render_comment(uniform_progress(done=True))


def test_only_the_latest_attempt_counts_toward_totals():
    """A job retried to success counts once, as a pass."""
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                job_progress(attempt(Status.FAILURE), attempt(Status.SUCCESS, number=2), target="ntp"),
            ),
        ),
        done=True,
    )

    body = render_comment(progress)

    assert "✅ 1 passed" in body
    assert "failed" not in body.replace("nothing failed", "")


@pytest.mark.parametrize(
    ("passed", "failed"),
    [(0, 1), (1, 0), (999, 1), (1, 999), (500, 500)],
)
def test_the_bar_is_exactly_its_width_and_never_drops_a_result(passed: int, failed: int):
    """One failure among a thousand passes still draws a sliver, and the bar never over-runs."""
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                *[job_progress(attempt(), target=f"pass-{index}") for index in range(passed)],
                *[job_progress(attempt(Status.FAILURE), target=f"fail-{index}") for index in range(failed)],
                status=Status.FAILURE if failed else Status.SUCCESS,
            ),
        ),
        done=True,
    )

    widths = _progress_bar_of(render_comment(progress))

    assert sum(widths.values()) == PROGRESS_BAR_WIDTH
    assert all(width >= 1 for width in widths.values())
    assert ("passed" in widths) is bool(passed)
    assert ("failed" in widths) is bool(failed)


def test_a_run_with_nothing_planned_draws_no_bar():
    body = render_comment(DispatcherProgress(batches=(), done=True))

    assert "progress-" not in body
    assert "_No batches were planned._" in body


# ---------------------------------------------------------------------------
# Size degradation: names go before links
# ---------------------------------------------------------------------------


def _many_failing(integrations: int, *, targets: int = 1, tests: int = 0) -> DispatcherProgress:
    """A failing run of a given shape, with test names distinct per target so nothing factors out."""
    jobs = []
    for integration in range(integrations):
        for target in range(targets):
            reports = (failing_report(*[f"test_{target}_{index}" for index in range(tests)]),) if tests else ()
            jobs.append(
                job_progress(
                    attempt(Status.FAILURE, reports=reports, failed_steps=("Run the tests",)),
                    target=f"integration-{integration:03d}",
                    environment=f"py3.13-{target}",
                )
            )
    return DispatcherProgress(batches=(batch_progress("batch-01", *jobs, status=Status.FAILURE),), done=True)


def _worst_case() -> DispatcherProgress:
    """More affected targets and test names than any tier can hold in full."""
    return _many_failing(120, targets=8, tests=20)


def test_the_compact_tier_drops_every_name_and_keeps_every_link():
    """The whole report at once, so a missing name never reads as a missing failure."""
    progress = _many_failing(3, targets=3, tests=2)
    full = render_comment(progress)
    compact = render_compact_comment(progress)

    assert "test_0_0" in full
    assert "test_0_0" not in compact
    assert "Run the tests" not in compact

    def links(body: str) -> list[str]:
        return [row.split(" · ")[0] for row in _target_rows_of(body)]

    assert links(compact) == links(full)
    assert compact.count(TARGET_JOB_URL) == 9
    # Something has to say what kind of failure it was, or the row says only that one happened.
    assert all("tests failed" in row for row in _target_rows_of(compact))


def test_the_truncated_tier_says_exactly_how_many_target_links_it_omitted():
    """A list that looks complete and is not is worse than a short one that admits it."""
    progress = _worst_case()
    body = render_truncated_comment(progress)

    notice = next(line for line in body.splitlines() if line.startswith("Showing "))
    match = re.fullmatch(
        r"Showing (\d+) of (\d+) affected targets\. "
        r"Open the failed batch links for the remaining (\d+)\.",
        notice,
    )
    assert match is not None, notice
    shown, total, remaining = (int(group) for group in match.groups())
    assert shown == len(_target_rows_of(body))
    assert total == 120 * 8
    assert shown + remaining == total


def test_the_truncated_tier_keeps_the_route_to_everything_it_dropped():
    """The batch links are what is left for a reader whose target did not make the cut."""
    body = render_truncated_comment(_worst_case())

    assert f"[batch-01]({BATCH_RUN_URL})" in _batch_strip_of(body)
    assert "test_0_0" not in body


def test_nothing_is_ever_hidden_inside_a_disclosure_of_its_own():
    """Hidden Markdown still spends the byte budget, so hiding a group saves a reader nothing.

    The renderer used to put every integration past the tenth behind a nested `Show N more`, which
    cost the same bytes as showing them and made the shape depend on a count rather than on size.
    """
    for body in (render_comment(_worst_case()), render_compact_comment(_worst_case())):
        assert "<summary>Show " not in body
        assert "+ 1 more" not in body


def test_the_renderer_degrades_on_its_own_rather_than_waiting_to_be_refused():
    """Local measurement and a refusal from GitHub walk the same ladder.

    A body over the limit that was only caught by the client would have been sent, refused, and
    re-rendered; catching it here means the same structure handles both.
    """
    small = render_comment(_many_failing(2, targets=2, tests=2))
    huge = render_comment(_worst_case())

    assert "test_0_0" in small
    # The names are what the ladder sheds first, and the links are what it keeps.
    assert "test_0_0" not in huge
    assert TARGET_JOB_URL in huge
    assert len(huge.encode("utf-8")) <= GITHUB_COMMENT_HARD_LIMIT


def test_each_tier_is_smaller_than_the_one_before():
    progress = _worst_case()
    compact = len(render_compact_comment(progress).encode("utf-8"))
    truncated = len(render_truncated_comment(progress).encode("utf-8"))

    assert truncated < compact


@pytest.mark.parametrize(
    "render",
    [
        pytest.param(render_comment, id="ladder"),
        pytest.param(render_truncated_comment, id="truncated"),
    ],
)
def test_what_is_published_always_fits_the_limit(render: Callable[[DispatcherProgress], str]):
    """The last tier packs against the budget, and the ladder never returns a body that overruns it.

    The middle tier is deliberately not budget-bound: it is one candidate the ladder measures, and
    the ladder is what keeps an oversized one from being sent.
    """
    assert len(render(_worst_case()).encode("utf-8")) <= GITHUB_COMMENT_HARD_LIMIT


def test_the_budget_is_measured_in_bytes_not_characters():
    """A body of multi-byte names is far larger than its character count suggests."""
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                *[
                    job_progress(
                        attempt(Status.FAILURE, reports=(failing_report("🧪" * 200),)),
                        target=f"integration-{index:03d}",
                    )
                    for index in range(400)
                ],
                status=Status.FAILURE,
            ),
        ),
        done=True,
    )

    body = render_comment(progress)

    assert len(body) < GITHUB_COMMENT_HARD_LIMIT
    assert len(body.encode("utf-8")) <= GITHUB_COMMENT_HARD_LIMIT


@pytest.mark.parametrize(
    "render",
    [
        pytest.param(render_comment, id="full"),
        pytest.param(render_compact_comment, id="compact"),
        pytest.param(render_truncated_comment, id="truncated"),
    ],
)
def test_every_tier_reports_itself_as_informational(render: Callable[[DispatcherProgress], str]):
    """Dispatcher does not decide merges yet, and no tier may drop the notice that says so."""
    assert "Dispatcher beta: informational only" in render(_worst_case())


@pytest.mark.parametrize(
    "render",
    [
        pytest.param(render_comment, id="full"),
        pytest.param(render_compact_comment, id="compact"),
        pytest.param(render_truncated_comment, id="truncated"),
    ],
)
def test_every_tier_admits_the_results_it_could_not_collect(render: Callable[[DispatcherProgress], str]):
    """The alert is in the header, which no tier truncates."""
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                *_many_failing(30, targets=4, tests=10).batches[0].jobs_progress,
                job_progress(attempt(error=ProgressError.NO_ARTIFACTS), target="kuma"),
                status=Status.FAILURE,
            ),
        ),
        done=True,
    )

    assert "Dispatcher could not collect test results for 1 target." in render(progress)


# ---------------------------------------------------------------------------
# Markdown safety and vocabulary
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "marker"),
    [
        pytest.param("test_plain", "test_plain", id="plain"),
        pytest.param("Run ``pytest`` <hack>", "Run ``pytest`` <hack>", id="double-backtick"),
        pytest.param("```", "```", id="fence"),
        pytest.param("</summary><script>x</script>", "script", id="html"),
        pytest.param("a`b", "a`b", id="single-backtick"),
    ],
)
def test_names_from_outside_cannot_break_out_of_their_code_span(raw: str, marker: str):
    """Test ids and step names come from outside, so they are data and never markup."""
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                job_progress(attempt(Status.FAILURE, failed_steps=(raw, "second step")), target="base"),
                status=Status.FAILURE,
            ),
        ),
        done=True,
    )

    body = render_comment(progress)
    rendered = MarkdownIt().render(body)

    assert marker in body
    # Whatever it contained, it rendered as text inside a code span rather than as an element.
    assert "<script>" not in rendered


def test_html_tags_are_balanced():
    progress = DispatcherProgress(
        batches=(batch_progress("batch-01", *_ddev_targets(), *_kafka_targets(), status=Status.FAILURE),),
        done=True,
    )

    body = render_comment(progress)

    for tag in ("details", "summary", "sub", "code"):
        assert body.count(f"<{tag}>") == body.count(f"</{tag}>"), tag


def test_a_disclosure_leaves_the_blank_line_github_needs_to_parse_it():
    """Without it GitHub renders the rows as one run-on line of literal text."""
    progress = DispatcherProgress(
        batches=(batch_progress("batch-01", *_ddev_targets(), status=Status.FAILURE),),
        done=True,
    )

    body = render_comment(progress)

    assert "</summary>\n\n- [" in body
    assert "\n\n</details>" in body


@pytest.mark.parametrize("phrase", INTERNAL_VOCABULARY)
def test_the_comment_uses_no_internal_vocabulary(phrase: str):
    """Dispatcher's own distinctions explain nothing to someone whose pull request is red."""
    bodies = [
        render_comment(_many_failing(3, targets=3, tests=2)),
        render_compact_comment(_worst_case()),
        render_truncated_comment(_worst_case()),
        render_comment(
            DispatcherProgress(
                batches=(
                    batch_progress("batch-01", _kuma_target(), error=ProgressError.NO_JOB_RESULTS),
                    batch_progress("batch-02", job_progress(attempt(), target="ntp"), status=Status.FAILURE),
                ),
                done=True,
            )
        ),
        *[render_shutdown_notice(shutdown_request(kind)) for kind in ShutdownKind],
    ]

    for body in bodies:
        assert phrase not in body.lower()


def test_no_internal_metadata_leaks_into_the_comment():
    """Revisions, job ids and attempt numbers are logged, not published."""
    progress = DispatcherProgress(
        batches=(
            batch_progress(
                "batch-01",
                job_progress(attempt(Status.FAILURE), attempt(Status.FAILURE, number=2), target="ntp"),
                status=Status.FAILURE,
                run_id=121,
            ),
        ),
        done=True,
    )

    body = render_comment(progress)

    assert "revision" not in body.lower()
    assert "job_id" not in body
    assert "attempt" not in body.lower()


def test_empty_snapshot_does_not_crash():
    body = render_comment(DispatcherProgress(batches=(), done=False))

    assert COMMENT_MARKER in body
    assert "_No batches were planned._" in body


# ---------------------------------------------------------------------------
# The footer, the log line and the run summary
# ---------------------------------------------------------------------------


def test_the_footer_of_a_finished_run_points_at_the_dispatcher_run(on_a_commit):
    """The commit tested and where Dispatcher ran are not available anywhere else in the comment."""
    body = render_comment(uniform_progress(done=True))

    assert body.endswith(f"<sub>Dispatcher finished on `ff9caa5` — [GitHub Run]({DISPATCH_RUN_URL}).</sub>")


def test_the_footer_says_what_it_can_outside_github_actions(monkeypatch):
    """Run locally there is no commit and no run to link, and the footer still has to close."""
    for variable in ("GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_SERVER_URL", "GITHUB_REPOSITORY"):
        monkeypatch.delenv(variable, raising=False)

    assert render_comment(uniform_progress(done=True)).endswith("<sub>Dispatcher finished.</sub>")


@pytest.mark.parametrize("kind", list(ShutdownKind), ids=lambda kind: kind.value)
def test_the_footer_of_a_stopped_run_names_the_terminal_state(kind: ShutdownKind, on_a_commit):
    body = render_comment(uniform_progress(complete=4), shutdown=shutdown_request(kind))

    assert f"<sub>Dispatcher {kind.value} on `ff9caa5`" in body


def test_summary_line_reports_state_and_counts():
    assert summary_line(uniform_progress(complete=4)) == (
        "Dispatcher tests in progress: 4/10 jobs, 4 passed, 0 failed, 0 skipped"
    )


@pytest.mark.parametrize("kind", list(ShutdownKind), ids=lambda kind: kind.value)
def test_summary_line_reports_a_stopped_run_as_stopped(kind: ShutdownKind):
    line = summary_line(uniform_progress(complete=4), shutdown=shutdown_request(kind))

    assert line.startswith(f"Dispatcher tests stopped ({kind.value}):")


def test_the_run_summary_is_the_comment_without_the_marker():
    """One renderer, so the run page and the pull request cannot disagree."""
    body = render_comment(_many_failing(2, targets=2, tests=1))

    summary = render_run_summary(body, pr_comment_failed=False)

    assert summary == body.removeprefix(COMMENT_MARKER).lstrip("\n")
    assert COMMENT_MARKER not in summary
    assert "<details>" in summary


def test_a_failed_comment_write_is_announced_above_the_report():
    """A reader who arrived from the run page has no other way to know a comment was attempted."""
    summary = render_run_summary(render_comment(uniform_progress(done=True)), pr_comment_failed=True)

    assert summary.startswith("> [!WARNING]\n> **The pull request comment could not be updated.**")
    assert "✅ Dispatcher tests: passed" in summary


def test_a_body_without_the_marker_is_passed_through_unharmed():
    """The run summary is also written from bodies the renderer did not produce."""
    assert render_run_summary("plain text", pr_comment_failed=False) == "plain text"


# ---------------------------------------------------------------------------
# Terminal states
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", list(ShutdownKind), ids=lambda kind: kind.value)
def test_a_stopped_run_says_so_in_one_short_sentence(kind: ShutdownKind):
    """How cancellation propagates is Dispatcher's business, not the reader's."""
    body = render_comment(uniform_progress(complete=4), shutdown=shutdown_request(kind))

    assert SHUTDOWN_HEADINGS[kind] in body
    alert = next(block for block in body.split("\n\n") if block.startswith("> [!CAUTION]"))
    assert len(alert.splitlines()) == 2
    assert "in progress" not in body


@pytest.mark.parametrize("kind", list(ShutdownKind), ids=lambda kind: kind.value)
def test_a_stopped_run_keeps_whatever_it_had_collected(kind: ShutdownKind):
    """The report below the alert is already only what arrived before the stop."""
    progress = DispatcherProgress(
        batches=(batch_progress("batch-01", *_ddev_targets(), status=Status.FAILURE),),
        done=False,
    )

    body = render_comment(progress, shutdown=shutdown_request(kind))

    assert "<code>ddev</code>" in body
    assert TARGET_JOB_URL in body


def test_a_fatal_error_reports_its_reason_and_a_timeout_does_not():
    """The reason is what distinguishes a crash from a deadline; a deadline explains itself."""
    failed = render_comment(uniform_progress(complete=4), shutdown=ShutdownRequest.failed(RuntimeError("boom")))
    timed_out = render_comment(uniform_progress(complete=4), shutdown=ShutdownRequest.timed_out(RuntimeError("boom")))

    assert FAILED_HEADING in failed
    assert "> Dispatcher stopped before completion: `boom`." in failed
    assert TIMED_OUT_HEADING in timed_out
    assert SHUTDOWN_ALERTS[ShutdownKind.TIMED_OUT] in timed_out
    assert "boom" not in timed_out


def test_a_terminal_reason_is_one_bounded_line():
    """A traceback would be noise, and an unbounded string could crowd out the results."""
    request = ShutdownRequest.failed(RuntimeError("x" * (SHUTDOWN_REASON_LIMIT * 3) + "\nsecond line"))

    body = render_shutdown_notice(request)

    alert = next(block for block in body.split("\n\n") if block.startswith("> [!CAUTION]"))
    assert len(alert.splitlines()) == 2
    assert len(alert) < SHUTDOWN_REASON_LIMIT + 100
    assert alert.endswith("...`.")


def test_a_terminal_reason_renders_as_literal_text_rather_than_markup():
    """An error string is data: it may contain backticks of its own."""
    request = ShutdownRequest.failed(RuntimeError("bad `config` value"))

    body = render_shutdown_notice(request)

    assert "``bad `config` value``" in body


@pytest.mark.parametrize("kind", list(ShutdownKind), ids=lambda kind: kind.value)
def test_a_stopped_run_with_nothing_collected_still_says_it_ran(kind: ShutdownKind):
    """No snapshot exists, so there is no report to attach the notice to."""
    body = render_shutdown_notice(shutdown_request(kind))

    assert body.startswith(COMMENT_MARKER)
    assert SHUTDOWN_HEADINGS[kind] in body
    assert "Batches · " not in body
    assert "<details>" not in body


def test_the_cancellation_alert_survives_every_tier():
    """A terminal state is the header's business, and no tier truncates the header."""
    progress = _worst_case()
    request = shutdown_request(ShutdownKind.CANCELLED)

    for render in (render_comment, render_compact_comment, render_truncated_comment):
        body = render(progress, shutdown=request)
        assert CANCELLED_HEADING in body
        assert SHUTDOWN_ALERTS[ShutdownKind.CANCELLED] in body
        assert FAILED_HEADING not in body


def test_a_snapshot_is_never_mutated_by_rendering():
    """Rendering happens outside the reporter's lock, so it must not touch what it is given."""
    progress = DispatcherProgress(
        batches=(batch_progress("batch-01", *_ddev_targets(), status=Status.FAILURE),),
        done=True,
    )
    before = dataclasses.asdict(progress)

    render_comment(progress)

    assert dataclasses.asdict(progress) == before
