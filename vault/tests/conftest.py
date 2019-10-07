# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
import requests

from datadog_checks.dev import docker_run, run_command
from datadog_checks.dev.conditions import WaitFor
from datadog_checks.vault import Vault

from .common import INSTANCES

HERE = os.path.dirname(os.path.abspath(__file__))
DOCKER_DIR = os.path.join(HERE, 'docker')


@pytest.fixture
def check():
    check = Vault('vault', {}, [INSTANCES['main']])
    return check


@pytest.fixture
def instance():
    return INSTANCES['main']


@pytest.fixture(scope='session', autouse=True)
def dd_environment():
    instance = INSTANCES['main']

    wait_and_unseal = WaitAndUnsealVault('{}/sys/health'.format(instance['api_url']))
    with docker_run(os.path.join(DOCKER_DIR, 'docker-compose.yaml'), conditions=[wait_and_unseal]):
        instance['client_token'] = wait_and_unseal.root_token
        yield instance


class WaitAndUnsealVault(WaitFor):
    def __init__(self, api_endpoint, attempts=60, wait=1):
        super(WaitAndUnsealVault, self).__init__(api_working, attempts, wait, args=(api_endpoint,))
        self.api_endpoint = api_endpoint
        self.root_token = None

    def __call__(self):
        # First wait for the api to be available
        super(WaitAndUnsealVault, self).__call__()

        # Then unseal the vault
        result = run_command("docker exec vault-leader vault operator init", capture=True)
        if result.stderr:
            raise Exception(result.stderr)
        result = result.stdout.split('\n')
        keys = [line.split(':')[1].strip() for line in result[:3]]
        for k in keys:
            err = run_command("docker exec vault-leader vault operator unseal {}".format(k), capture=True).stderr
            if err:
                raise Exception("Can't unseal vault-leader. \n{}".format(err))
            err = run_command("docker exec vault-replica vault operator unseal {}".format(k), capture=True).stderr
            if err:
                raise Exception("Can't unseal vault-replica. \n{}".format(err))

        root_token = [line for line in result if 'Initial Root Token' in line]
        if not root_token:
            raise Exception("Can't find root token in vault output")
        self.root_token = root_token[0].split(':')[1].strip()

        return True


def api_working(api_endpoint):
    response = requests.get(api_endpoint, timeout=1).json()
    if response:
        return True
    return False
