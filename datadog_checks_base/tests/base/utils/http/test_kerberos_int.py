# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.dev.utils import ON_WINDOWS

pytestmark = [pytest.mark.integration]


@pytest.mark.skipif(ON_WINDOWS, reason='Test cannot be run on Windows')
def test_kerberos_auth_noconf(kerberos):
    instance = {}
    init_config = {}
    http = RequestsWrapper(instance, init_config)
    response = http.get(kerberos["url"])

    assert response.status_code == 401


@pytest.mark.skipif(ON_WINDOWS, reason='Test cannot be run on Windows')
def test_kerberos_auth_principal_inexistent(kerberos):
    instance = {
        'url': kerberos["url"],
        'auth_type': 'kerberos',
        'kerberos_auth': 'required',
        'kerberos_hostname': kerberos["hostname"],
        'kerberos_cache': "DIR:{}".format(kerberos["cache"]),
        'kerberos_keytab': kerberos["keytab"],
        'kerberos_principal': "user/doesnotexist@{}".format(kerberos["realm"]),
        'kerberos_force_initiate': 'false',
    }
    init_config = {}
    http = RequestsWrapper(instance, init_config)
    response = http.get(instance["url"])
    assert response.status_code == 401


@pytest.mark.skipif(ON_WINDOWS, reason='Test cannot be run on Windows')
def test_kerberos_auth_principal_incache_nokeytab(kerberos):
    instance = {
        'url': kerberos["url"],
        'auth_type': 'kerberos',
        'kerberos_auth': 'required',
        'kerberos_cache': "DIR:{}".format(kerberos["cache"]),
        'kerberos_hostname': kerberos["hostname"],
        'kerberos_principal': "user/nokeytab@{}".format(kerberos["realm"]),
        'kerberos_force_initiate': 'true',
    }
    init_config = {}
    http = RequestsWrapper(instance, init_config)
    response = http.get(instance["url"])
    assert response.status_code == 200


@pytest.mark.skipif(ON_WINDOWS, reason='Test cannot be run on Windows')
def test_kerberos_auth_principal_inkeytab_nocache(kerberos):
    instance = {
        'url': kerberos["url"],
        'auth_type': 'kerberos',
        'kerberos_auth': 'required',
        'kerberos_hostname': kerberos["hostname"],
        'kerberos_cache': "DIR:{}".format(kerberos["tmp_dir"]),
        'kerberos_keytab': kerberos["keytab"],
        'kerberos_principal': "user/inkeytab@{}".format(kerberos["realm"]),
        'kerberos_force_initiate': 'true',
    }
    init_config = {}
    http = RequestsWrapper(instance, init_config)
    response = http.get(instance["url"])
    assert response.status_code == 200


@pytest.mark.skipif(True, reason='Test fixture for Agent QA only')
def test_kerberos_auth_with_agent(kerberos_agent):
    """
    Test setup to verify kerberos authorization from an actual Agent container.

    Steps to reproduce:
    1. Change decorator above from `True` to `False` to enable test
    2. Edit compose/kerberos-agent/Dockerfile to appropriate Agent release
    3. Run test via `ddev test -k test_kerberos_auth_with_agent datadog_checks_base:py38`
    4. After compose builds, and during `time.sleep` exec into Agent container in separate shell
       via `docker exec -it compose_agent_1 /bin/bash`
    5. Execute check via `agent check nginx` and verify successful result.
    6. Exit test via Ctrl-C (test will show as failed, but that's okay)

    NOTE: if encountering issues (GSS auth error, nginx 403 error, ...), delete the images for the Agent, KDC
    and nginx containers, and try again to start off from fresh images.
    """
    import time

    time.sleep(3600)

    # Assertion just to provide logical breakpoint.
    assert True
