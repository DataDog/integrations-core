# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest
import os
import requests
import time

from datadog_checks.linkerd import LinkerdCheck

# 3p
import docker

CHECK_NAME = 'linkerd'

PROMETHEUS_ENDPOINT = 'http://127.0.0.1:9990/admin/metrics/prometheus'

INSTANCES = [{
    'prometheus_endpoint': PROMETHEUS_ENDPOINT,
}]

INIT_CONFIG = {'linkerd_prometheus_prefix': 'dd_linkerd_'}


def wait_for(url, max_retries):
    retries = 0
    success = False
    while not success and retries < max_retries:
        try:
            r = requests.get(url)
            success = r.ok
        except Exception:
            pass
        time.sleep(1)
        retries += 1
    if retries == max_retries:
        raise Exception('Service not up after {} retries'.format(retries))

@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator

@pytest.fixture(scope="module")
def linkerd(request):
    client = docker.from_env()
    container = client.containers.run(
        image="buoyantio/linkerd:1.3.5",
        command="/config.yaml",
        detach=True,
        name="dd-linkerd-test",
        ports={'9990/tcp': 9990},
        volumes={
            os.path.dirname(os.path.realpath(__file__)) + '/config.yaml': {
                'bind': '/config.yaml',
                'mode': 'ro'
            }
        })

    def teardown():
        container.kill()
        container.remove()
        pass
    request.addfinalizer(teardown)
    wait_for(PROMETHEUS_ENDPOINT, 30)
    return container


def test_check(linkerd, aggregator):
    linkerd_check = LinkerdCheck('linkerd', INIT_CONFIG, {}, INSTANCES)
    linkerd_check.check(INSTANCES[0])
    aggregator.assert_metric('linkerd.jvm.start_time')
