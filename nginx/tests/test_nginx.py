# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import sys
import json
import subprocess
import time

import mock
import pytest
import requests

from datadog_checks.stubs import aggregator as _aggregator
from datadog_checks.nginx import Nginx, VTS_METRIC_MAP
from datadog_checks.utils.common import get_docker_hostname


HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES_PATH = os.path.join(HERE, 'fixtures')

NGINX_HOST = get_docker_hostname()
NGINX_PORT = '8080'
NGINX_PORT_SSL = '8081'
TAGS = ['foo', 'bar']

DOCKER_COMPOSE_ARGS = [
    "docker-compose",
    "-f", os.path.join(HERE, 'docker', 'docker-compose.yaml')
]


@pytest.fixture(scope="session")
def nginx():
    env = os.environ
    env['NGINX_CONFIG_FOLDER'] = os.path.join(HERE, 'docker', 'nginx')

    start_nginx(env)
    yield
    subprocess.check_call(DOCKER_COMPOSE_ARGS + ["down"], env=env)


@pytest.fixture(scope="session")
def nginx_vts():
    env = os.environ
    env['NGINX_CONFIG_FOLDER'] = os.path.join(HERE, 'nginx_vts')

    start_nginx(env)
    yield
    subprocess.check_call(DOCKER_COMPOSE_ARGS + ["down"], env=env)


def start_nginx(env):
    subprocess.check_call(DOCKER_COMPOSE_ARGS + ["up", "-d"], env=env)

    sys.stderr.write("Waiting for NGINX to boot...")

    attempts = 1
    while True:
        if attempts >= 10:
            subprocess.check_call(DOCKER_COMPOSE_ARGS + ["down"], env=env)
            raise Exception("NGINX failed to boot...")

        try:
            res = requests.get('http://{}:{}/nginx_status'.format(NGINX_HOST, NGINX_PORT))
            res.raise_for_status
            break
        except Exception:
            attempts += 1
            time.sleep(1)


@pytest.fixture
def aggregator():
    _aggregator.reset()
    return _aggregator


@pytest.fixture
def instance():
    return {
        'nginx_status_url': 'http://{}:{}/nginx_status'.format(NGINX_HOST, NGINX_PORT),
        'tags': TAGS,
    }


@pytest.fixture
def instance_ssl():
    return {
        'nginx_status_url': 'https://{}:{}/nginx_status'.format(NGINX_HOST, NGINX_PORT_SSL),
        'tags': TAGS,
    }


@pytest.fixture
def instance_vts():
    return {
        'nginx_status_url': 'http://{}:{}/vts_status'.format(NGINX_HOST, NGINX_PORT),
        'tags': TAGS,
        'use_vts': True,
    }


@pytest.fixture
def check():
    return Nginx('nginx', {}, {})


def test_connect(check, instance, aggregator, nginx):
    """
    Testing that connection will work with instance
    """
    check.check(instance)
    aggregator.assert_metric("nginx.net.connections", tags=TAGS, count=1)
    extra_tags = ['host:{}'.format(NGINX_HOST), 'port:{}'.format(NGINX_PORT)]
    aggregator.assert_service_check('nginx.can_connect', tags=TAGS+extra_tags)


def test_connect_ssl(check, instance_ssl, aggregator, nginx):
    """
    Testing ssl connection
    """
    instance_ssl['ssl_validation'] = False
    check.check(instance_ssl)
    aggregator.assert_metric("nginx.net.connections", tags=TAGS, count=1)

    # assert ssl validation throws an error
    with pytest.raises(requests.exceptions.SSLError):
        instance_ssl['ssl_validation'] = True
        check.check(instance_ssl)


def test_flatten_json(check):
    with open(os.path.join(FIXTURES_PATH, 'nginx_plus_in.json')) as f:
        parsed = check.parse_json(f.read())
        parsed.sort()

    with open(os.path.join(FIXTURES_PATH, 'nginx_plus_out.python')) as f:
        expected = eval(f.read())

    # Check that the parsed test data is the same as the expected output
    assert parsed == expected


def mocked_perform_request(*args, **kwargs):
    """
    A mocked version of _perform_request
    """
    response = mock.MagicMock()
    url = args[1]

    if "/2/nginx" in url:
        file_contents = open(os.path.join(FIXTURES_PATH, 'plus_api_nginx.json')).read()
        response.json.return_value = json.loads(file_contents)
    elif "/2/processes" in url:
        file_contents = open(os.path.join(FIXTURES_PATH, 'plus_api_processes.json')).read()
        response.json.return_value = json.loads(file_contents)
    elif "/2/connections" in url:
        file_contents = open(os.path.join(FIXTURES_PATH, 'plus_api_connections.json')).read()
        response.json.return_value = json.loads(file_contents)
    elif "/2/ssl" in url:
        file_contents = open(os.path.join(FIXTURES_PATH, 'plus_api_ssl.json')).read()
        response.json.return_value = json.loads(file_contents)
    elif "/2/slabs" in url:
        file_contents = open(os.path.join(FIXTURES_PATH, 'plus_api_slabs.json')).read()
        response.json.return_value = json.loads(file_contents)
    elif "/2/http/requests" in url:
        file_contents = open(os.path.join(FIXTURES_PATH, 'plus_api_http_requests.json')).read()
        response.json.return_value = json.loads(file_contents)
    elif "/2/http/server_zones" in url:
        file_contents = open(os.path.join(FIXTURES_PATH, 'plus_api_http_server_zones.json')).read()
        response.json.return_value = json.loads(file_contents)
    elif "/2/http/caches" in url:
        file_contents = open(os.path.join(FIXTURES_PATH, 'plus_api_http_caches.json')).read()
        response.json.return_value = json.loads(file_contents)
    elif "/2/http/upstreams" in url:
        file_contents = open(os.path.join(FIXTURES_PATH, 'plus_api_http_upstreams.json')).read()
        response.json.return_value = json.loads(file_contents)
    elif "/2/stream/upstreams" in url:
        file_contents = open(os.path.join(FIXTURES_PATH, 'plus_api_stream_upstreams.json')).read()
        response.json.return_value = json.loads(file_contents)
    elif "/2/stream/server_zones" in url:
        file_contents = open(os.path.join(FIXTURES_PATH, 'plus_api_stream_server_zones.json')).read()
        response.json.return_value = json.loads(file_contents)
    else:
        response.json.return_value = ""

    return response


def test_plus_api(check, instance, aggregator):
    instance['use_plus_api'] = True
    check._perform_request = mock.MagicMock(side_effect=mocked_perform_request)
    check.check(instance)

    all = 0
    for m in aggregator.metric_names:
        all += len(aggregator.metrics(m))
    assert all == 1180


def test_nest_payload(check):
    keys = ["foo", "bar"]
    payload = {
        "key1": "val1",
        "key2": "val2"
    }

    result = check._nest_payload(keys, payload)
    expected = {
        "foo": {
            "bar": payload
        }
    }

    assert result == expected


@pytest.mark.skipif('nginx-vts' not in os.environ.get('NGINX_IMAGE', ''), reason="Not using VTS")
def test_vts(check, instance_vts, aggregator, nginx_vts):
    check.check(instance_vts)

    # skip metrics that are difficult to reproduce in a test environment
    skip_metrics = [
        'nginx.upstream.peers.responses.1xx',
        'nginx.upstream.peers.responses.2xx',
        'nginx.upstream.peers.responses.3xx',
        'nginx.upstream.peers.responses.4xx',
        'nginx.upstream.peers.responses.5xx',
        'nginx.upstream.peers.requests',
        'nginx.upstream.peers.received',
        'nginx.server_zone.received',
        'nginx.server_zone.responses.1xx',
        'nginx.server_zone.responses.2xx',
        'nginx.server_zone.responses.3xx',
        'nginx.server_zone.responses.4xx',
        'nginx.server_zone.responses.5xx',
        'nginx.server_zone.requests',
        'nginx.server_zone.sent',
        'nginx.upstream.peers.sent',
        'nginx.upstream.peers.health_checks.last_passed',
        'nginx.upstream.peers.weight',
        'nginx.upstream.peers.backup',
    ]

    print(aggregator.metric_names)

    for vts, mapped in VTS_METRIC_MAP.items():
        if mapped in skip_metrics:
            continue
        aggregator.assert_metric(mapped, tags=TAGS)
