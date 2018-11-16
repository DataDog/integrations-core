# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import requests

from datadog_checks.dev import docker_run
from .common import COMPOSE_FILE, URL, V3_PREVIEW


@pytest.fixture(scope='session', autouse=True)
def dd_environment(instance):
    if V3_PREVIEW:
        endpoints = '{}/metrics'.format(URL)
    else:
        endpoints = (
            '{}/v2/stats/self'.format(URL),
            '{}/v2/stats/store'.format(URL),
        )

    with docker_run(COMPOSE_FILE, endpoints=endpoints):
        if not V3_PREVIEW:
            requests.post('{}/v2/keys/message'.format(URL), data={'value': 'Hello world'})

        yield instance


@pytest.fixture(scope='session')
def instance():
    if V3_PREVIEW:
        return {
            'use_preview': True,
            'prometheus_url': '{}/metrics'.format(URL),
        }
    else:
        return {
            'url': URL,
        }
