# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Direct unit tests for `dispatch.extract_run_urls`.

The CLI-level tests in `test_command.py` only ever raise `httpx.HTTPStatusError` (an
`Exception`) from the dispatch call, so they do not exercise the
`BaseException`-but-not-`Exception` re-raise guard that lets `CancelledError` and
`KeyboardInterrupt` propagate. These tests pin that contract on the helper directly.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from ddev.cli.release.test_agent.dispatch import extract_run_urls
from ddev.utils.github_async import GitHubResponse
from ddev.utils.github_async.models import WorkflowDispatchResult


def _ok(html_url: str) -> GitHubResponse[WorkflowDispatchResult]:
    return GitHubResponse(
        data=WorkflowDispatchResult(
            workflow_run_id=1,
            run_url=f'https://api.github.com/{html_url}',
            html_url=html_url,
        ),
        headers={},
    )


def test_extract_run_urls_returns_both_html_urls() -> None:
    results = [_ok('https://github.com/x/runs/1'), _ok('https://github.com/x/runs/2')]

    assert extract_run_urls(results) == ('https://github.com/x/runs/1', 'https://github.com/x/runs/2')


@pytest.mark.parametrize(
    'flow_control_exc',
    [
        pytest.param(asyncio.CancelledError('user pressed ctrl-c'), id='cancelled-error'),
        pytest.param(KeyboardInterrupt(), id='keyboard-interrupt'),
    ],
)
@pytest.mark.parametrize(
    'position',
    [
        pytest.param('linux', id='linux-cancelled'),
        pytest.param('windows', id='windows-cancelled'),
    ],
)
def test_extract_run_urls_reraises_flow_control_exceptions(flow_control_exc: BaseException, position: str) -> None:
    """`CancelledError` / `KeyboardInterrupt` in either slot must propagate verbatim, not be wrapped."""
    other = _ok('https://github.com/x/runs/sibling')
    if position == 'linux':
        results: list[Any] = [flow_control_exc, other]
    else:
        results = [other, flow_control_exc]

    with pytest.raises(type(flow_control_exc)):
        extract_run_urls(results)


def test_extract_run_urls_wraps_regular_exception_failure_as_runtime_error() -> None:
    """Sanity check that the `Exception` branch still produces a wrapped RuntimeError."""
    err = RuntimeError('forbidden')
    results = [err, _ok('https://github.com/x/runs/2')]

    with pytest.raises(RuntimeError, match=r'Linux dispatch failed:.*forbidden.*runs/2'):
        extract_run_urls(results)


def test_extract_run_urls_both_failures_includes_both_reprs() -> None:
    """Both-fail must surface both error reprs in the RuntimeError message (not via __notes__)."""
    linux_err = RuntimeError('linux-side detail')
    windows_err = RuntimeError('windows-side detail')

    with pytest.raises(RuntimeError) as excinfo:
        extract_run_urls([linux_err, windows_err])

    message = str(excinfo.value)
    assert 'Both dispatches failed' in message
    assert 'linux-side detail' in message
    assert 'windows-side detail' in message
