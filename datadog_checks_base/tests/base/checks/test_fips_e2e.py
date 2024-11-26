# -*- coding: utf-8 -*-

# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import sys
from typing import Any  # noqa: F401

import pytest
import requests

from datadog_checks.base import AgentCheck
from datadog_checks.dev import docker_run, get_here
from datadog_checks.dev.conditions import WaitForPortListening

HERE = get_here()
EMBEDDED = os.path.join(HERE, '..', '..', 'fixtures', 'fips', 'embedded')
FIPS_SERVER_PORT = 8443


@pytest.fixture(scope="session")
def non_fips_server():
    conditions = [WaitForPortListening("localhost", 443)]
    with docker_run(os.path.join(HERE, 'docker', 'fips_compose.yaml'), conditions=conditions):
        yield


@pytest.mark.e2e
@pytest.mark.skipif(not sys.platform == "linux", reason="only testing on Linux")
def test_connection_before_fips():
    """
    Test connection to the FIPS server before enabling FIPS mode.
    """
    url = f"https://localhost:{FIPS_SERVER_PORT}"
    try:
        response = requests.get(url, verify=False, timeout=5)
        assert response.status_code == 200
    except requests.exceptions.SSLError as e:
        pytest.fail(f"Connection failed due to SSL error: {e}")


@pytest.mark.e2e
@pytest.mark.skipif(not sys.platform == "linux", reason="only testing on Linux")
def test_connection_after_fips():
    """
    Test connection to the FIPS server after enabling FIPS mode.
    """
    os.environ["OPENSSL_CONF"] = os.path.join(EMBEDDED, 'ssl', 'openssl.cnf')
    os.environ["OPENSSL_MODULES"] = os.path.join(EMBEDDED, 'lib', 'ossl-modules')
    os.environ["GOFIPS"] = "1"
    AgentCheck()

    url = f"https://localhost:{FIPS_SERVER_PORT}"
    try:
        response = requests.get(url, verify=False, timeout=5)
        assert response.status_code == 200
    except requests.exceptions.SSLError as e:
        pytest.fail(f"Connection failed due to SSL error: {e}")
