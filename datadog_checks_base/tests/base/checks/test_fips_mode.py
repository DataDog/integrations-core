# -*- coding: utf-8 -*-

# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import subprocess
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


@pytest.fixture(scope="session", autouse=True)
def create_fipsmodule_config():
    command = [
        "openssl",
        "fipsinstall",
        "-module",
        f'{EMBEDDED}/lib/ossl-modules/fips.so',
        "-out",
        f'{EMBEDDED}/ssl/fipsmodule.cnf',
        "-provider_name",
        "fips",
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        error_message = (
            f"Failed to set up FIPS mode. Exiting tests.\n"
            f"Command: {' '.join(command)}\n"
            f"Return Code: {e.returncode}\n"
            f"Output: {e.stdout}\n"
            f"Error: {e.stderr}\n"
        )
        pytest.exit(error_message, returncode=1)
    yield


@pytest.fixture(scope="session", autouse=True)
def non_fips_server():
    conditions = [WaitForPortListening("localhost", 443)]
    with docker_run(os.path.join(HERE, 'docker', 'fips_compose.yaml'), conditions=conditions):
        yield


@pytest.fixture(scope="function", autouse=True)
def clean_environment():
    os.environ["GOFIPS"] = "0"
    AgentCheck().fips.disable()
    yield


@pytest.mark.skipif(not sys.platform == "linux", reason="only testing on Linux")
def test_md5_before_fips():
    import ssl

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.set_ciphers("MD5")
    assert True


@pytest.mark.skipif(not sys.platform == "linux", reason="only testing on Linux")
def test_md5_after_fips():
    import ssl

    AgentCheck().fips.enable(path_to_embedded=EMBEDDED)
    with pytest.raises(ssl.SSLError, match='No cipher can be selected.'):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.set_ciphers("MD5")


@pytest.mark.skipif(not sys.platform == "linux", reason="only testing on Linux")
def test_cryptography_md5_cryptography():
    from cryptography.hazmat.primitives import hashes

    hashes.Hash(hashes.MD5())


@pytest.mark.skipif(not sys.platform == "linux", reason="only testing on Linux")
def test_cryptography_md5_fips():
    from cryptography.exceptions import InternalError
    from cryptography.hazmat.primitives import hashes

    AgentCheck().fips.enable(path_to_embedded=EMBEDDED)
    with pytest.raises(InternalError, match='Unknown OpenSSL error.'):
        hashes.Hash(hashes.MD5())


@pytest.mark.skipif(not sys.platform == "linux", reason="only testing on Linux")
def test_connection_before_fips():
    """
    Test connection to the non-FIPS server before enabling FIPS mode.
    """
    url = f"https://localhost:{FIPS_SERVER_PORT}"
    try:
        response = requests.get(url, verify=False, timeout=5)
        assert response.status_code == 200
    except requests.exceptions.SSLError as e:
        pytest.fail(f"Connection failed due to SSL error: {e}")


@pytest.mark.skipif(not sys.platform == "linux", reason="only testing on Linux")
def test_connection_after_fips():
    """
    Test connection to the non-FIPS server after enabling FIPS mode.
    """
    os.environ["OPENSSL_CONF"] = os.path.join(EMBEDDED, 'ssl', 'openssl.cnf')
    os.environ["OPENSSL_MODULES"] = os.path.join(EMBEDDED, 'lib', 'ossl-modules')
    os.environ["GOFIPS"] = "1"
    AgentCheck()

    url = f"https://localhost:{FIPS_SERVER_PORT}"
    try:
        response = requests.get(url, verify=False, timeout=5)
        assert response.status_code != 200
    except requests.exceptions.SSLError as e:
        pytest.fail(f"Connection failed due to SSL error: {e}")
