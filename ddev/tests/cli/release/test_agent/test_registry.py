# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import httpx
import pytest
from pytest_mock import MockerFixture

from ddev.cli.release.test_agent.registry import list_agent_rc_tags, manifest_exists


def _response(status: int, json_body: object | None = None, method: str = 'HEAD') -> httpx.Response:
    request = httpx.Request(method, 'https://registry.datadoghq.com/v2/agent/manifests/x')
    kwargs: dict[str, object] = {'request': request}
    if json_body is not None:
        kwargs['json'] = json_body
    return httpx.Response(status, **kwargs)


@pytest.mark.parametrize(
    'status_code, expected',
    [
        pytest.param(200, True, id='exists'),
        pytest.param(404, False, id='missing'),
    ],
)
def test_manifest_exists_resolves_status(mocker: MockerFixture, status_code: int, expected: bool) -> None:
    mocker.patch('httpx.head', return_value=_response(status_code))

    assert manifest_exists('7.80.0-rc.1') is expected


@pytest.mark.parametrize('status', [401, 403, 500, 503])
def test_manifest_exists_raises_on_other_errors(mocker: MockerFixture, status: int) -> None:
    mocker.patch('httpx.head', return_value=_response(status))

    with pytest.raises(httpx.HTTPStatusError):
        manifest_exists('7.80.0-rc.1')


def test_list_agent_rc_tags_filters_and_sorts(mocker: MockerFixture) -> None:
    payload = {
        'name': 'agent',
        'tags': [
            '7.79.0-rc.1',
            '7.80.0-rc.10',
            '7.80.0-rc.2',
            '7.80.0-rc.1',
            '7.80.0',
            '7.80.0-rc.1-servercore',
            '7-rc',
            'latest',
        ],
    }
    mocker.patch('httpx.get', return_value=_response(200, json_body=payload, method='GET'))

    result = list_agent_rc_tags(7, 80)

    assert result == ['7.80.0-rc.1', '7.80.0-rc.2', '7.80.0-rc.10']


@pytest.mark.parametrize(
    'payload',
    [
        pytest.param({'name': 'agent', 'tags': []}, id='empty-list'),
        pytest.param({'name': 'agent', 'tags': None}, id='null-tags'),
        pytest.param({'name': 'agent'}, id='missing-key'),
    ],
)
def test_list_agent_rc_tags_handles_missing_tags(mocker: MockerFixture, payload: dict[str, object]) -> None:
    mocker.patch('httpx.get', return_value=_response(200, json_body=payload, method='GET'))

    assert list_agent_rc_tags(7, 99) == []
