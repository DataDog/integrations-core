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
from datadog_checks.nginx import Nginx


HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES_PATH = os.path.join(HERE, 'fixtures')

NGINX_HOST = os.getenv('DOCKER_HOSTNAME', 'localhost')
NGINX_PORT = '8080'
NGINX_PORT_SSL = '8081'
TAGS = ['foo', 'bar']


@pytest.fixture(scope="session")
def nginx():
    env = os.environ
    env['NGINX_CONFIG_FOLDER'] = os.path.join(HERE, 'nginx')

    args = [
        "docker-compose",
        "-f", os.path.join(HERE, 'docker-compose.yaml')
    ]
    subprocess.check_call(args + ["up", "-d"], env=env)

    sys.stderr.write("Waiting for NGINX to boot...")

    attempts = 1
    while True:
        if attempts >= 10:
            subprocess.check_call(args + ["down"], env=env)
            raise Exception("NGINX failed to boot...")

        try:
            res = requests.get('http://{}:{}/nginx_status'.format(NGINX_HOST, NGINX_PORT))
            res.raise_for_status
            break
        except Exception:
            attempts += 1
            time.sleep(1)

    yield

    subprocess.check_call(args + ["down"], env=env)


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
    print(url)

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
    assert all == 956


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
