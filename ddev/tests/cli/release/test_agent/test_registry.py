# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the agent-specific wrapper around `ddev.utils.docker_registry`.

The registry transport itself is covered by `tests/utils/test_docker_registry.py`.
These tests focus on the RC filter and version sort layered on top.
"""

from __future__ import annotations

import httpx
import pytest
from pytest_mock import MockerFixture

from ddev.cli.release.test_agent.registry import list_agent_rc_tags, manifest_exists


def test_manifest_exists_delegates_to_utility(mocker: MockerFixture) -> None:
    spy = mocker.patch('ddev.utils.docker_registry.manifest_exists', return_value=True)

    assert manifest_exists('7.80.0-rc.1') is True
    spy.assert_called_once_with('agent', '7.80.0-rc.1', timeout=10.0)


def test_list_agent_rc_tags_filters_and_sorts(mocker: MockerFixture) -> None:
    mocker.patch(
        'ddev.utils.docker_registry.list_tags',
        return_value=[
            '7.79.0-rc.1',
            '7.80.0-rc.10',
            '7.80.0-rc.2',
            '7.80.0-rc.1',
            '7.80.0',
            '7.80.0-rc.1-servercore',
            '7-rc',
            'latest',
        ],
    )

    assert list_agent_rc_tags(7, 80) == ['7.80.0-rc.1', '7.80.0-rc.2', '7.80.0-rc.10']


@pytest.mark.parametrize(
    'all_tags',
    [
        pytest.param([], id='empty-list'),
        pytest.param(['7.79.0-rc.1', '7.81.0-rc.1', 'latest'], id='no-matching-minor'),
    ],
)
def test_list_agent_rc_tags_returns_empty_when_no_match(mocker: MockerFixture, all_tags: list[str]) -> None:
    mocker.patch('ddev.utils.docker_registry.list_tags', return_value=all_tags)

    assert list_agent_rc_tags(7, 80) == []


@pytest.mark.parametrize(
    'exc',
    [
        pytest.param(httpx.ConnectError('connection refused'), id='connect-error'),
        pytest.param(httpx.ReadTimeout('read timed out'), id='read-timeout'),
    ],
)
def test_list_agent_rc_tags_propagates_network_errors(mocker: MockerFixture, exc: Exception) -> None:
    mocker.patch('ddev.utils.docker_registry.list_tags', side_effect=exc)

    with pytest.raises(type(exc)):
        list_agent_rc_tags(7, 80)
