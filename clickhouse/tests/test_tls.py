# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.clickhouse import ClickhouseCheck

from . import common
from .common import tls

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


@tls
def test_connect_with_verify_false(aggregator, tls_instance, dd_run_check):
    """Regression: verify: false must allow connection to a self-signed cert.

    Integration-level proof that the pool manager fix works end-to-end: the shared
    pool must be created with verify=False so clickhouse-connect doesn't override it
    with a cert_reqs=CERT_REQUIRED pool when pool_mgr is pre-supplied.
    """
    tls_instance['verify'] = False
    check = ClickhouseCheck('clickhouse', {}, [tls_instance])
    dd_run_check(check)
    aggregator.assert_service_check('clickhouse.can_connect', status=ClickhouseCheck.OK)


@tls
def test_connect_ssl_verify_true_fails(tls_instance, dd_run_check):
    """Sanity: verify=True (default) must reject a self-signed cert.

    Confirms TLS is actually active — without this passing, test_connect_with_verify_false
    would be vacuous (the server might just be accepting plain HTTP).
    """
    tls_instance['verify'] = True
    check = ClickhouseCheck('clickhouse', {}, [tls_instance])
    with pytest.raises(Exception):
        dd_run_check(check)


@tls
def test_connect_verify_true_with_ca_cert(aggregator, tls_instance, dd_run_check):
    """Production path: verify=True + tls_ca_cert pointing at a trusted CA must succeed.

    Most TLS-using DBM customers configure the integration this way — TLS on, cert
    validation on, with a custom CA bundle that trusts the server's cert. Pins that
    path against the self-signed server so the ca_cert plumbing in the shared pool
    manager doesn't silently regress.
    """
    tls_instance['verify'] = True
    tls_instance['tls_ca_cert'] = common.SERVER_CERT_PATH
    check = ClickhouseCheck('clickhouse', {}, [tls_instance])
    dd_run_check(check)
    aggregator.assert_service_check('clickhouse.can_connect', status=ClickhouseCheck.OK)
