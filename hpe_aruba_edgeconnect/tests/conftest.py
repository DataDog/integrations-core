# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import ssl
from unittest.mock import MagicMock
from urllib.request import urlopen

import pytest

from datadog_checks.dev import WaitFor, docker_run, get_docker_hostname, get_here
from datadog_checks.dev.utils import find_free_port
from datadog_checks.hpe_aruba_edgeconnect import HpeArubaEdgeconnectCheck
from datadog_checks.hpe_aruba_edgeconnect.client import OrchestratorClient

from .constants import (
    APPLIANCE_PAYLOAD,
    CHECK_MODULE,
    DISK_PAYLOAD,
    MEMORY_PAYLOAD,
    NEWEST_TS,
    TGZ_DATA,
    _build_cpu_payload,
    _build_system_info,
)

USE_EDGECONNECT_LAB = os.environ.get('USE_EDGECONNECT_LAB')


HERE = get_here()
HOST = get_docker_hostname()
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')
EXCLUDED_APPLIANCE_IP = '10.0.0.3'


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
        appliance_ip = f'{HOST}:{appliance_port}'

        def _ready():
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            urlopen(f'https://{orch_ip}/health', timeout=2, context=ctx)
            urlopen(f'https://{appliance_ip}/health', timeout=2, context=ctx)

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
                'APPLIANCE_IP': appliance_ip,
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


# ---------------------------------------------------------------------------
# Unit test helpers
# ---------------------------------------------------------------------------


def _mock_orch_client(appliance_payload, overlay_config=None):
    overlays_response = MagicMock(
        raise_for_status=MagicMock(),
        json=MagicMock(return_value=overlay_config if overlay_config is not None else []),
    )

    def http_get(url, **kwargs):
        if url.endswith('/gms/rest/gms/overlays/config'):
            return overlays_response
        raise AssertionError(f'unexpected orchestrator GET request: {url}')

    http = MagicMock()
    http.get.side_effect = http_get
    client = OrchestratorClient(http, 'localhost:8443')
    client.get_appliances = MagicMock(return_value=appliance_payload)
    return client


def _mock_appliance_client(
    tgz_data,
    newest_timestamp=NEWEST_TS,
    cpu=50,
    mem=None,
    disk=None,
    alarms=None,
    system_info=None,
    app_ip='10.0.0.1',
):
    client = MagicMock()
    client.get_newest_timestamp.return_value = newest_timestamp
    if isinstance(tgz_data, dict):
        client.get_minute_stats.side_effect = lambda fname: tgz_data[fname]
    else:
        client.get_minute_stats.return_value = tgz_data
    client.get_network_interfaces.return_value = {
        'ifInfo': [{'ifname': 'wan0', 'admin': 1, 'oper': 1, 'speed': '1000Mb/s (auto)'}]
    }
    client.get_cpu_stats.return_value = _build_cpu_payload(cpu)
    client.get_memory_stats.return_value = mem if mem is not None else MEMORY_PAYLOAD
    client.get_disk_usage.return_value = disk if disk is not None else DISK_PAYLOAD
    client.get_alarms.return_value = (
        alarms if alarms is not None else {'outstanding': [{'type': 'HW'}, {'type': 'TUNNEL'}]}
    )
    client.get_system_info.return_value = system_info if system_info is not None else _build_system_info(app_ip)
    client.get_interface_labels.return_value = {'wan': {}, 'lan': {}}
    client.app_ip = app_ip
    return client


def _setup_mocks(
    mocker,
    check,
    appliance_payload,
    tgz_bytes=None,
    appliance_client=None,
    overlay_config=None,
    cached_timestamp=None,
):
    orch = _mock_orch_client(appliance_payload, overlay_config)
    mocker.patch(f'{CHECK_MODULE}.OrchestratorClient', return_value=orch)
    check._orch_client = None

    if appliance_client is not None:
        mocker.patch.object(check, '_create_appliance_client', return_value=appliance_client)
    elif tgz_bytes is not None:
        mocker.patch.object(check, '_create_appliance_client', return_value=_mock_appliance_client(tgz_bytes))

    mocker.patch.object(check, 'read_persistent_cache', return_value=cached_timestamp)
    mocker.patch.object(check, 'write_persistent_cache')
    return orch


# ---------------------------------------------------------------------------
# Unit test fixtures
# ---------------------------------------------------------------------------


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
