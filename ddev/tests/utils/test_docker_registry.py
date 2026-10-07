# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the generic Docker Registry v2 helpers in `ddev.utils.docker_registry`."""

from __future__ import annotations

import httpx
import pytest
from pytest_mock import MockerFixture

from ddev.utils import docker_registry
from ddev.utils.network import REQUEST_ATTEMPTS

TRANSIENT_ERROR_PARAMS = [
    pytest.param(httpx.ConnectError('[WinError 10054] connection forcibly closed'), id='connect-error'),
    pytest.param(httpx.ConnectTimeout('connect timed out'), id='connect-timeout'),
    pytest.param(httpx.ReadError('read error'), id='read-error'),
    pytest.param(httpx.ReadTimeout('read timed out'), id='read-timeout'),
    pytest.param(httpx.RemoteProtocolError('peer closed connection'), id='remote-protocol-error'),
]

ATTEMPTS = REQUEST_ATTEMPTS


def _response(
    status: int,
    *,
    json_body: object | None = None,
    headers: dict[str, str] | None = None,
    method: str = 'GET',
    url: str = 'https://registry.datadoghq.com/v2/agent/tags/list',
) -> httpx.Response:
    request = httpx.Request(method, url)
    kwargs: dict[str, object] = {'request': request}
    if json_body is not None:
        kwargs['json'] = json_body
    if headers is not None:
        kwargs['headers'] = headers
    return httpx.Response(status, **kwargs)


@pytest.mark.parametrize(
    'status_code, expected',
    [
        pytest.param(200, True, id='exists'),
        pytest.param(404, False, id='missing'),
    ],
)
def test_manifest_exists_resolves_status(mocker: MockerFixture, status_code: int, expected: bool) -> None:
    mocker.patch('httpx.head', return_value=_response(status_code, method='HEAD'))

    assert docker_registry.manifest_exists('agent', '7.80.0-rc.1') is expected


@pytest.mark.parametrize('status', [401, 403, 500, 503])
def test_manifest_exists_raises_on_other_errors(mocker: MockerFixture, status: int) -> None:
    mocker.patch('httpx.head', return_value=_response(status, method='HEAD'))

    with pytest.raises(httpx.HTTPStatusError):
        docker_registry.manifest_exists('agent', '7.80.0-rc.1')


@pytest.mark.parametrize('exc', TRANSIENT_ERROR_PARAMS)
def test_manifest_exists_propagates_network_errors(mocker: MockerFixture, exc: Exception) -> None:
    """A failure that outlives the retries still surfaces, and the retries stay bounded."""
    head = mocker.patch('httpx.head', side_effect=exc)

    with pytest.raises(type(exc)):
        docker_registry.manifest_exists('agent', '7.80.0-rc.1')

    assert head.call_count == ATTEMPTS


@pytest.mark.parametrize('exc', TRANSIENT_ERROR_PARAMS)
def test_manifest_exists_retries_a_transient_failure(mocker: MockerFixture, exc: Exception) -> None:
    head = mocker.patch('httpx.head', side_effect=[exc, _response(200, method='HEAD')])

    assert docker_registry.manifest_exists('agent', '7.80.0-rc.1') is True
    assert head.call_count == 2


@pytest.mark.parametrize(
    'status, expected',
    [
        pytest.param(404, False, id='withdrawn-tag'),
        pytest.param(500, None, id='server-error'),
    ],
)
def test_manifest_exists_does_not_retry_a_served_response(
    mocker: MockerFixture, status: int, expected: bool | None
) -> None:
    """A status the registry actually served is final; only connection failures are retried.

    Retrying a 404 would let a withdrawn tag look like a network blip and cost three
    round trips to reach the same answer.
    """
    head = mocker.patch('httpx.head', return_value=_response(status, method='HEAD'))

    if expected is None:
        with pytest.raises(httpx.HTTPStatusError):
            docker_registry.manifest_exists('agent', '7.80.0-rc.1')
    else:
        assert docker_registry.manifest_exists('agent', '7.80.0-rc.1') is expected

    assert head.call_count == 1


def test_manifest_exists_uses_custom_host(mocker: MockerFixture) -> None:
    spy = mocker.patch('httpx.head', return_value=_response(200, method='HEAD'))

    docker_registry.manifest_exists('repo', 'tag', host='private.registry.example')

    spy.assert_called_once()
    assert spy.call_args.args[0] == 'https://private.registry.example/v2/repo/manifests/tag'


def test_list_tags_returns_single_page(mocker: MockerFixture) -> None:
    mocker.patch('httpx.get', return_value=_response(200, json_body={'name': 'agent', 'tags': ['a', 'b', 'c']}))

    assert docker_registry.list_tags('agent') == ['a', 'b', 'c']


@pytest.mark.parametrize(
    'payload',
    [
        pytest.param({'name': 'agent', 'tags': []}, id='empty-list'),
        pytest.param({'name': 'agent', 'tags': None}, id='null-tags'),
        pytest.param({'name': 'agent'}, id='missing-key'),
    ],
)
def test_list_tags_handles_missing_tags(mocker: MockerFixture, payload: dict[str, object]) -> None:
    mocker.patch('httpx.get', return_value=_response(200, json_body=payload))

    assert docker_registry.list_tags('agent') == []


def test_list_tags_follows_relative_link_header(mocker: MockerFixture) -> None:
    """A `Link: </v2/...>; rel="next"` header on page 1 must be followed before returning."""
    page_1 = _response(
        200,
        json_body={'name': 'agent', 'tags': ['a', 'b']},
        headers={'Link': '</v2/agent/tags/list?n=2&last=b>; rel="next"'},
    )
    page_2 = _response(
        200,
        json_body={'name': 'agent', 'tags': ['c', 'd']},
    )
    get = mocker.patch('httpx.get', side_effect=[page_1, page_2])

    result = docker_registry.list_tags('agent', page_size=2)

    assert result == ['a', 'b', 'c', 'd']
    assert get.call_count == 2
    assert get.call_args_list[1].args[0] == 'https://registry.datadoghq.com/v2/agent/tags/list?n=2&last=b'


def test_list_tags_follows_absolute_link_header(mocker: MockerFixture) -> None:
    page_1 = _response(
        200,
        json_body={'name': 'agent', 'tags': ['a']},
        headers={'Link': '<https://other.example/v2/agent/tags/list?last=a>; rel="next"'},
    )
    page_2 = _response(200, json_body={'name': 'agent', 'tags': ['b']})
    get = mocker.patch('httpx.get', side_effect=[page_1, page_2])

    result = docker_registry.list_tags('agent')

    assert result == ['a', 'b']
    assert get.call_args_list[1].args[0] == 'https://other.example/v2/agent/tags/list?last=a'


def test_list_tags_stops_when_link_header_absent(mocker: MockerFixture) -> None:
    """If the final page omits the Link header, iteration ends — no infinite loop."""
    page = _response(200, json_body={'name': 'agent', 'tags': ['only']})
    get = mocker.patch('httpx.get', return_value=page)

    result = docker_registry.list_tags('agent')

    assert result == ['only']
    assert get.call_count == 1


def test_list_tags_ignores_non_next_link_relations(mocker: MockerFixture) -> None:
    """Other rels like `last`, `prev`, `up` must not be followed as if they were `next`."""
    page = _response(
        200,
        json_body={'name': 'agent', 'tags': ['only']},
        headers={'Link': '</v2/agent/tags/list?last=z>; rel="last", </v2/agent/tags/list>; rel="prev"'},
    )
    get = mocker.patch('httpx.get', return_value=page)

    result = docker_registry.list_tags('agent')

    assert result == ['only']
    assert get.call_count == 1


@pytest.mark.parametrize('exc', TRANSIENT_ERROR_PARAMS)
def test_list_tags_propagates_network_errors(mocker: MockerFixture, exc: Exception) -> None:
    get = mocker.patch('httpx.get', side_effect=exc)

    with pytest.raises(type(exc)):
        docker_registry.list_tags('agent')

    assert get.call_count == ATTEMPTS


@pytest.mark.parametrize('exc', TRANSIENT_ERROR_PARAMS)
def test_list_tags_retries_a_transient_failure(mocker: MockerFixture, exc: Exception) -> None:
    get = mocker.patch('httpx.get', side_effect=[exc, _response(200, json_body={'name': 'agent', 'tags': ['a']})])

    assert docker_registry.list_tags('agent') == ['a']
    assert get.call_count == 2


def test_list_tags_retries_each_page_independently(mocker: MockerFixture) -> None:
    """A blip while fetching page 2 must not discard page 1 or restart pagination."""
    page_1 = _response(
        200,
        json_body={'name': 'agent', 'tags': ['a']},
        headers={'Link': '</v2/agent/tags/list?last=a>; rel="next"'},
    )
    page_2 = _response(200, json_body={'name': 'agent', 'tags': ['b']})
    get = mocker.patch('httpx.get', side_effect=[page_1, httpx.ConnectError('connection reset'), page_2])

    assert docker_registry.list_tags('agent') == ['a', 'b']
    assert get.call_count == 3
    assert get.call_args_list[2].args[0] == 'https://registry.datadoghq.com/v2/agent/tags/list?last=a'


def test_list_tags_does_not_retry_a_served_error(mocker: MockerFixture) -> None:
    get = mocker.patch('httpx.get', return_value=_response(503))

    with pytest.raises(httpx.HTTPStatusError):
        docker_registry.list_tags('agent')

    assert get.call_count == 1
