# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import getpass
import os
import time

import pytest
import requests

from datadog_checks.dev import LazyFunction, TempDir, docker_run, run_command
from datadog_checks.dev.conditions import WaitFor
from datadog_checks.dev.utils import ON_WINDOWS, create_file, running_on_ci
from datadog_checks.vault import Vault

from .common import COMPOSE_FILE, HEALTH_ENDPOINT, INSTANCES, get_vault_server_config_file
from .utils import get_client_token_path, set_client_token_path


@pytest.fixture(scope='session')
def check():
    return lambda inst: Vault('vault', {}, [inst])


@pytest.fixture(scope='session')
def global_tags():
    tags = ['api_url:{}'.format(INSTANCES['main']['api_url'])]
    tags.extend(INSTANCES['main']['tags'])
    return tags


@pytest.fixture(scope='session')
def instance():
    def get_instance():
        inst = INSTANCES['main'].copy()
        inst['client_token_path'] = get_client_token_path()
        return inst

    return get_instance


@pytest.fixture(scope='session')
def no_token_instance():
    inst = INSTANCES['main'].copy()
    inst['no_token'] = True
    return inst


@pytest.fixture(scope='session')
def e2e_instance():
    inst = INSTANCES['main'].copy()
    inst['client_token_path'] = '/home/vault-sink/token'
    return inst


@pytest.fixture(scope='session')
def dd_environment(e2e_instance):
    with TempDir('vault-jwt') as jwt_dir, TempDir('vault-sink') as sink_dir:
        token_file = os.path.join(sink_dir, 'token')

        if not os.path.exists(token_file):
            os.chmod(sink_dir, 0o777)
            create_file(token_file)
            os.chmod(token_file, 0o777)

        with docker_run(
            COMPOSE_FILE,
            env_vars={'JWT_DIR': jwt_dir, 'SINK_DIR': sink_dir, 'SERVER_CONFIG_FILE': get_vault_server_config_file()},
            conditions=[WaitAndUnsealVault(HEALTH_ENDPOINT), ApplyPermissions(token_file)],
            sleep=10,
            mount_logs=True,
        ):
            set_client_token_path(token_file)

            yield e2e_instance, {'docker_volumes': ['{}:/home/vault-sink'.format(sink_dir)]}


class ApplyPermissions(LazyFunction):
    def __init__(self, token_file):
        self.token_file = token_file

    def __call__(self):
        if not ON_WINDOWS:
            user = getpass.getuser()
            chown_args = ['chown', user, self.token_file]

            if user != 'root' and running_on_ci():
                chown_args.insert(0, 'sudo')

            run_command(chown_args, check=True)


class WaitAndUnsealVault(WaitFor):
    def __init__(self, api_endpoint, attempts=60, wait=1):
        super(WaitAndUnsealVault, self).__init__(api_working, attempts, wait, args=(api_endpoint,))
        self.api_endpoint = api_endpoint

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

            time.sleep(2)

            err = run_command("docker exec vault-replica vault operator unseal {}".format(k), capture=True).stderr
            if err:
                raise Exception("Can't unseal vault-replica. \n{}".format(err))

            time.sleep(2)

        root_token = [line for line in result if 'Initial Root Token' in line]
        if not root_token:
            raise Exception("Can't find root token in vault output")
        root_token = root_token[0].split(':')[1].strip()

        # Set up auto-auth
        for command in (
            'login {}'.format(root_token),
            'policy write metrics /home/metrics_policy.hcl',
            'audit enable file file_path=/vault/vault-audit.log',
            'auth enable jwt',
            'write auth/jwt/config jwt_supported_algs=RS256 jwt_validation_pubkeys=@/home/pub.pem',
            'write auth/jwt/role/datadog role_type=jwt bound_audiences=test user_claim=name token_policies=metrics',
            'agent -config=/home/agent_config.hcl',
        ):
            time.sleep(2)
            run_command('docker exec vault-leader vault {}'.format(command), capture=True, check=True)


def api_working(api_endpoint):
    response = requests.get(api_endpoint, timeout=1).json()
    if response:
        return True
    return False
