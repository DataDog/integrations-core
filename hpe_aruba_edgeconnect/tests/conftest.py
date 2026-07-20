# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import ssl
from urllib.request import urlopen

import pytest

from datadog_checks.dev import WaitFor, docker_run, get_docker_hostname, get_here
from datadog_checks.dev.utils import find_free_port
from datadog_checks.hpe_aruba_edgeconnect import HpeArubaEdgeconnectCheck

from .common import (
    APPLIANCE_PAYLOAD,
    EXCLUDED_APPLIANCE_IP,
    TGZ_DATA,
    _mock_appliance_client,
    _setup_mocks,
)

USE_EDGECONNECT_LAB = os.environ.get('USE_EDGECONNECT_LAB')


HERE = get_here()
HOST = get_docker_hostname()
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')


@pytest.fixture(scope='session')
def dd_environment(instance, dd_save_state):
    if USE_EDGECONNECT_LAB:
        orch_ip = os.environ['EDGECONNECT_ORCH_IP']
        orch_username = os.environ['EDGECONNECT_ORCH_USERNAME']
        orch_password = os.environ['EDGECONNECT_ORCH_PASSWORD']
        appliance_username = os.environ.get('EDGECONNECT_APPLIANCE_USERNAME', orch_username)
        appliance_password = os.environ.get('EDGECONNECT_APPLIANCE_PASSWORD', orch_password)
        appliance_credentials = [
            {'cidr': '0.0.0.0/0', 'username': appliance_username, 'password': appliance_password},
        ]
        inst = instance(
            orch_ip,
            orchestrator_username=orch_username,
            orchestrator_password=orch_password,
            appliance_credentials_overrides=appliance_credentials,
            send_ndm_metadata=True,
            collect_events=True,
        )
        dd_save_state('e2e_instance', inst)
        yield {
            'instances': [inst],
            'logs': [
                {
                    'type': 'tcp',
                    'port': 10514,
                    'service': 'edgeconnect',
                    'source': 'aruba_edgeconnect',
                }
            ],
        }
    else:
        orch_port = find_free_port(HOST)
        appliance_port = find_free_port(HOST)
        orch_ip = f'{HOST}:{orch_port}'

        def _ready():
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            urlopen(f'https://{orch_ip}/health', timeout=2, context=ctx)
            urlopen(f'https://{HOST}:{appliance_port}/health', timeout=2, context=ctx)

        inst = instance(
            orch_ip,
            connect_timeout=2,
            appliance_ips={'exclude': [f'{EXCLUDED_APPLIANCE_IP}/32']},
        )

        with docker_run(
            compose_file=COMPOSE_FILE,
            build=True,
            conditions=[WaitFor(_ready, attempts=60, wait=1)],
            env_vars={
                'HOST_PORT': str(orch_port),
                'APPLIANCE_PORT': str(appliance_port),
                'ORCH_USERNAME': 'admin',
                'ORCH_PASSWORD': '',
                'APPLIANCE_USERNAME': 'admin',
                'APPLIANCE_PASSWORD': '',
            },
        ):
            yield {'instances': [inst]}


@pytest.fixture(scope='session')
def instance():
    def builder(
        orchestrator_ip: str,
        orchestrator_username: str = 'admin',
        orchestrator_password: str = '',
        appliance_ips=None,
        appliance_credentials=None,
        send_ndm_metadata: bool = False,
        **kwargs,
    ) -> dict:
        inst = {
            'orchestrator_ip': orchestrator_ip,
            'orchestrator_username': orchestrator_username,
            'orchestrator_password': orchestrator_password,
            'tls_verify': False,
            'send_ndm_metadata': send_ndm_metadata,
            **kwargs,
        }
        if appliance_ips is not None:
            inst['appliance_ips'] = appliance_ips if isinstance(appliance_ips, dict) else {'include': appliance_ips}
        if appliance_credentials is not None:
            inst['appliance_credentials_overrides'] = appliance_credentials
        return inst

    return builder


@pytest.fixture
def check(instance):
    inst = instance('localhost:8443', appliance_ips=['10.0.0.1'], max_backfill_minutes=10)
    return HpeArubaEdgeconnectCheck('hpe_aruba_edgeconnect', {}, [inst])


@pytest.fixture
def all_metrics_aggregator(dd_run_check, aggregator, mocker, check):
    client = _mock_appliance_client(TGZ_DATA)
    _setup_mocks(
        mocker,
        check,
        APPLIANCE_PAYLOAD,
        appliance_client=client,
        cached_timestamp='99999940',
        overlay_config=[
            {'id': 0, 'name': 'business'},
            {'name': 'BulkData', 'trafficClass': 2},
            {'name': 'RealTime', 'trafficClass': 4},
        ],
    )
    dd_run_check(check)
    return aggregator
