# C Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License see LICENSE

import os
import pytest
from requests import Response

CHECK_NAME = 'cisco_aci'

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')
CAPACITY_FIXTURES_DIR = os.path.join(FIXTURES_DIR, 'capacity')
FABRIC_FIXTURES_DIR = os.path.join(FIXTURES_DIR, 'fabric')
TENANT_FIXTURES_DIR = os.path.join(FIXTURES_DIR, 'tenant')
ALL_FICTURE_DIR = [FIXTURES_DIR, CAPACITY_FIXTURES_DIR, FABRIC_FIXTURES_DIR, TENANT_FIXTURES_DIR]

USERNAME = 'datadog'
PASSWORD = 'datadog'
ACI_URL = 'https://datadoghq.com'
ACI_URLS = [ACI_URL]
CONFIG = {
    'aci_urls': ACI_URLS,
    'username': USERNAME,
    'pwd': PASSWORD,
    'tenant': [
        'DataDog',
    ]
}

CONFIG_WITH_TAGS = {
    'aci_urls': ACI_URLS,
    'username': USERNAME,
    'pwd': PASSWORD,
    'tenant': [
        'DataDog',
    ],
    "tags": ["project:cisco_aci"],
}


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


def mock_send(prepped_request, **kwargs):
    if prepped_request.path_url == '/api/aaaLogin.xml':
        cookie_path = os.path.join(FIXTURES_DIR, 'login_cookie.txt')
        response_path = os.path.join(FIXTURES_DIR, 'login.txt')
        response = Response()
        with open(cookie_path, 'r') as f:
            response.cookies = {'APIC-cookie': f.read()}
        with open(response_path, 'r') as f:
            response.raw = f.read()

    return response
