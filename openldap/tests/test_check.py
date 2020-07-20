# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import ldap3
import pytest

from datadog_checks.base.utils.platform import Platform

from .common import _check

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator, check, instance):
    tags = ["url:{}".format(instance["url"]), "test:integration"]
    check.check(instance)
    _check(aggregator, check, tags)


@pytest.mark.usefixtures('dd_environment')
def test_check_ssl(aggregator, check, instance_ssl):
    tags = ["url:{}".format(instance_ssl["url"]), "test:integration"]
    # Should fail certificate verification
    with pytest.raises(ldap3.core.exceptions.LDAPExceptionError):
        check.check(instance_ssl)
        aggregator.assert_service_check("openldap.can_connect", check.CRITICAL, tags=tags)
    instance_ssl["ssl_verify"] = False
    # Should work now
    check.check(instance_ssl)
    aggregator.assert_service_check("openldap.can_connect", check.OK, tags=tags)


@pytest.mark.usefixtures('dd_environment')
def test_check_connection_failure(aggregator, check, instance):
    instance["url"] = "bad_url"
    tags = ["url:{}".format(instance["url"]), "test:integration"]
    # Should fail certificate verification
    with pytest.raises(ldap3.core.exceptions.LDAPExceptionError):
        check.check(instance)
        aggregator.assert_service_check("openldap.can_connect", check.CRITICAL, tags=tags)


@pytest.mark.skipif(not Platform.is_linux(), reason='Windows sockets are not file handles')
@pytest.mark.usefixtures('dd_environment')
def test_check_socket(aggregator, check, instance):
    host_socket_path = os.path.join(os.environ['HOST_SOCKET_DIR'], 'ldapi')
    instance["url"] = "ldapi://{}".format(host_socket_path)
    tags = ["url:{}".format(instance["url"]), "test:integration"]
    check.check(instance)
    aggregator.assert_service_check("openldap.can_connect", check.OK, tags=tags)
