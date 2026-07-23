# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import base64
import copy
import http.client
import json
import os
import ssl
import urllib.error
import urllib.request
from typing import Any

import mock
import pytest
from packaging import version

from datadog_checks.base.utils.common import exclude_undefined_keys
from datadog_checks.dev import WaitFor, docker_run
from datadog_checks.dev.http import MockHTTPResponse
from datadog_checks.elastic import ESCheck

from .common import (
    CLUSTER_TAG,
    ELASTIC_CLUSTER_TAG,
    ELASTIC_FLAVOR,
    ELASTIC_VERSION,
    HERE,
    PASSWORD,
    URL,
    USER,
    get_fixture_path,
)

CUSTOM_TAGS = ['foo:bar', 'baz']

INSTANCE = {
    'url': URL,
    'username': USER,
    'password': PASSWORD,
    'tags': CUSTOM_TAGS,
    'tls_verify': False,
    'custom_queries': [
        {
            'endpoint': '/_search',
            'data_path': 'hits.total',
            'columns': [
                {'value_path': 'value', 'name': 'elasticsearch.custom.metric', 'type': 'gauge'},
                {'value_path': 'relation', 'name': 'dynamic_tag', 'type': 'tag'},
            ],
        },
    ],
}


BENCHMARK_INSTANCE = {
    'url': URL,
    'username': USER,
    'password': PASSWORD,
    'tags': CUSTOM_TAGS,
    'tls_verify': False,
}


class HttpResponse:
    def __init__(self, url: str, status_code: int, reason: str, content: bytes) -> None:
        self.url = url
        self.status_code = status_code
        self.reason = reason or http.client.responses.get(status_code, '')
        self.content = content

    @property
    def text(self) -> str:
        return self.content.decode('utf-8')

    def json(self) -> Any:
        return json.loads(self.text)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise urllib.error.HTTPError(self.url, self.status_code, self.reason, http.client.HTTPMessage(), None)


def http_request(
    url: str,
    method: str = 'GET',
    *,
    auth: tuple[str, str] | None = None,
    json_data: Any = None,
    verify: bool = True,
) -> HttpResponse:
    request_headers = {}
    body = None
    if json_data is not None:
        body = json.dumps(json_data).encode('utf-8')
        request_headers['Content-Type'] = 'application/json'

    if auth is not None:
        username, password = auth
        token = base64.b64encode('{}:{}'.format(username, password).encode('utf-8')).decode('ascii')
        request_headers['Authorization'] = 'Basic {}'.format(token)

    context = ssl._create_unverified_context() if not verify and url.startswith('https://') else None
    open_kwargs: dict[str, Any] = {}
    if context is not None:
        open_kwargs['context'] = context

    req = urllib.request.Request(url, data=body, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(req, **open_kwargs) as response:
            return HttpResponse(url, response.getcode(), response.reason, response.read())
    except urllib.error.HTTPError as error:
        return HttpResponse(url, error.code, error.reason, error.read())


def ping_elastic():
    """
    The PUT request we use to ping the server will create an index named `testindex`
    as soon as ES is available. This is just one possible ping strategy but it's needed
    as a fixture for tests that require that index to exist in order to pass.
    """
    response = http_request('{}/testindex'.format(URL), method='PUT', auth=(USER, PASSWORD), verify=False)
    response.raise_for_status()


def create_slm():
    if version.parse(ELASTIC_VERSION) < version.parse('7.4.0'):
        return

    create_backup_body = {"type": "fs", "settings": {"location": "data"}}
    response = http_request(
        '{}/_snapshot/my_repository?pretty'.format(INSTANCE['url']),
        method='PUT',
        json_data=create_backup_body,
        auth=(INSTANCE['username'], INSTANCE['password']),
        verify=False,
    )
    response.raise_for_status()

    create_slm_body = {
        "schedule": "0 30 1 * * ?",
        "name": "<daily-snap-{now/d}>",
        "repository": "my_repository",
        "config": {"indices": ["data-*", "important"], "ignore_unavailable": False, "include_global_state": False},
        "retention": {"expire_after": "30d", "min_count": 5, "max_count": 50},
    }
    response = http_request(
        '{}/_slm/policy/daily-snapshots?pretty'.format(INSTANCE['url']),
        method='PUT',
        json_data=create_slm_body,
        auth=(INSTANCE['username'], INSTANCE['password']),
        verify=False,
    )
    response.raise_for_status()


def index_starts_with_dot():
    create_dot_testindex = http_request('{}/.testindex'.format(URL), method='PUT', auth=(USER, PASSWORD), verify=False)
    create_dot_testindex.raise_for_status()


@pytest.fixture(scope='session')
def dd_environment():
    # opensearch doesn't play well with xpack env vars
    compose_file = '{}-docker-compose.yaml'.format(ELASTIC_FLAVOR)
    compose_file = os.path.join(HERE, 'compose', compose_file)

    with docker_run(
        compose_file=compose_file,
        conditions=[
            WaitFor(ping_elastic, attempts=100),
            WaitFor(index_starts_with_dot, attempts=100),
            WaitFor(create_slm, attempts=5),
        ],
        attempts=2,
        attempts_wait=10,
    ):
        yield INSTANCE


@pytest.fixture
def elastic_check():
    return ESCheck('elastic', {}, instances=[INSTANCE])


@pytest.fixture
def instance():
    return copy.deepcopy(INSTANCE)


@pytest.fixture
def mock_es_endpoints(mock_http_response_per_endpoint):
    """
    Mock every endpoint a default `ESCheck.check()` run hits, with representative data, so unit tests can
    exercise the whole check through `dd_run_check` and target specific behavior purely through the instance
    config. Pass `overrides` (keyed by full URL) to swap individual responses, for example to simulate an error.
    """

    def setup(overrides=None):
        responses = {
            # `_get_es_version` probes the base URL.
            URL: [MockHTTPResponse(json_data={'version': {'number': '8.8.0'}})],
            # Node stats: the local URL is used by default, the cluster-wide one when `cluster_stats` is on.
            '{}/_nodes/_local/stats'.format(URL): [MockHTTPResponse(file_path=get_fixture_path('stats_v8.json'))],
            '{}/_nodes/stats'.format(URL): [MockHTTPResponse(file_path=get_fixture_path('stats_v8.json'))],
            '{}/_cat/templates?format=json'.format(URL): [
                MockHTTPResponse(file_path=get_fixture_path('templates.json'))
            ],
            # A single-node cluster reports `yellow`; `green` would make the health service check OK, and the
            # aggregator stub rejects an OK service check that carries a message.
            '{}/_cluster/health'.format(URL): [
                MockHTTPResponse(
                    json_data={
                        'cluster_name': 'test-cluster',
                        'status': 'yellow',
                        'active_primary_shards': 1,
                        'active_shards': 1,
                        'relocating_shards': 0,
                        'initializing_shards': 0,
                        'unassigned_shards': 1,
                        'number_of_nodes': 1,
                        'number_of_data_nodes': 1,
                        'timed_out': False,
                    }
                )
            ],
            # `pending_task_stats` defaults to on, so the check always hits this endpoint.
            '{}/_cluster/pending_tasks'.format(URL): [MockHTTPResponse(json_data={'tasks': []})],
            # The default `instance` fixture ships a `/_search` custom query.
            '{}/_search'.format(URL): [MockHTTPResponse(json_data={'hits': {'total': {'value': 0, 'relation': 'eq'}}})],
        }
        if overrides:
            responses.update(overrides)
        mock_http_response_per_endpoint(responses)

    return setup


@pytest.fixture
def benchmark_elastic_check():
    return ESCheck('elastic', {}, instances=[BENCHMARK_INSTANCE])


@pytest.fixture
def benchmark_instance():
    return copy.deepcopy(BENCHMARK_INSTANCE)


@pytest.fixture
def instance_normalize_hostname():
    return {
        'url': URL,
        'username': USER,
        'password': PASSWORD,
        'tags': CUSTOM_TAGS,
        'node_name_as_host': True,
        'tls_verify': False,
    }


@pytest.fixture
def version_metadata():
    if '-' in ELASTIC_VERSION:
        base, release = ELASTIC_VERSION.split('-')
        parts = base.split('.')
    else:
        release = None
        parts = ELASTIC_VERSION.split('.')

    major = parts[0]
    minor = parts[1] if len(parts) > 1 else mock.ANY
    patch = parts[2] if len(parts) > 2 else mock.ANY
    return exclude_undefined_keys(
        {
            'version.scheme': 'semver',
            'version.major': major,
            'version.minor': minor,
            'version.patch': patch,
            'version.raw': mock.ANY,
            'version.release': release,
        }
    )


def _cluster_tags():
    tags = ['url:{}'.format(URL)] + ELASTIC_CLUSTER_TAG + CLUSTER_TAG
    tags.extend(CUSTOM_TAGS)

    return tags


@pytest.fixture
def new_cluster_tags():
    tags = ['url:{}'.format(URL)] + ELASTIC_CLUSTER_TAG
    tags.extend(CUSTOM_TAGS)

    return tags


@pytest.fixture
def cluster_tags():
    return _cluster_tags()


@pytest.fixture
def node_tags():
    tags = _cluster_tags()
    tags.append('node_name:test-node')
    return tags


@pytest.fixture
def slm_tags():
    tags = _cluster_tags()
    tags.append('policy:daily-snapshots')
    tags.append('repository:my_repository')
    return tags
