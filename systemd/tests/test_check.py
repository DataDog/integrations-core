# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import ldap3
import pytest

from datadog_checks.utils.platform import Platform

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator, check, instance):
    tags = ["url:{}".format(instance["url"]), "test:integration"]
    check.check(instance)
    aggregator.assert_service_check("openldap.can_connect", check.OK, tags=tags)
    aggregator.assert_metric("openldap.bind_time", tags=tags)
    aggregator.assert_metric("openldap.connections.current", tags=tags)
    aggregator.assert_metric("openldap.connections.max_file_descriptors", tags=tags)
    aggregator.assert_metric("openldap.connections.total", tags=tags)
    aggregator.assert_metric("openldap.operations.completed.total", tags=tags)
    aggregator.assert_metric("openldap.operations.initiated.total", tags=tags)
    aggregator.assert_metric("openldap.operations.completed", tags=tags + ["operation:abandon"])
    aggregator.assert_metric("openldap.operations.initiated", tags=tags + ["operation:abandon"])
    aggregator.assert_metric("openldap.operations.completed", tags=tags + ["operation:add"])
    aggregator.assert_metric("openldap.operations.initiated", tags=tags + ["operation:add"])
    aggregator.assert_metric("openldap.operations.completed", tags=tags + ["operation:bind"])
    aggregator.assert_metric("openldap.operations.initiated", tags=tags + ["operation:bind"])
    aggregator.assert_metric("openldap.operations.completed", tags=tags + ["operation:compare"])
    aggregator.assert_metric("openldap.operations.initiated", tags=tags + ["operation:compare"])
    aggregator.assert_metric("openldap.operations.completed", tags=tags + ["operation:delete"])
    aggregator.assert_metric("openldap.operations.initiated", tags=tags + ["operation:delete"])
    aggregator.assert_metric("openldap.operations.completed", tags=tags + ["operation:extended"])
    aggregator.assert_metric("openldap.operations.initiated", tags=tags + ["operation:extended"])
    aggregator.assert_metric("openldap.operations.completed", tags=tags + ["operation:modify"])
    aggregator.assert_metric("openldap.operations.initiated", tags=tags + ["operation:modify"])
    aggregator.assert_metric("openldap.operations.completed", tags=tags + ["operation:modrdn"])
    aggregator.assert_metric("openldap.operations.initiated", tags=tags + ["operation:modrdn"])
    aggregator.assert_metric("openldap.operations.completed", tags=tags + ["operation:search"])
    aggregator.assert_metric("openldap.operations.initiated", tags=tags + ["operation:search"])
    aggregator.assert_metric("openldap.operations.completed", tags=tags + ["operation:unbind"])
    aggregator.assert_metric("openldap.operations.initiated", tags=tags + ["operation:unbind"])
    aggregator.assert_metric("openldap.statistics.bytes", tags=tags)
    aggregator.assert_metric("openldap.statistics.entries", tags=tags)
    aggregator.assert_metric("openldap.statistics.pdu", tags=tags)
    aggregator.assert_metric("openldap.statistics.referrals", tags=tags)
    aggregator.assert_metric("openldap.threads", tags=tags + ["status:active"])
    aggregator.assert_metric("openldap.threads", tags=tags + ["status:backload"])
    aggregator.assert_metric("openldap.threads", tags=tags + ["status:open"])
    aggregator.assert_metric("openldap.threads", tags=tags + ["status:pending"])
    aggregator.assert_metric("openldap.threads", tags=tags + ["status:starting"])
    aggregator.assert_metric("openldap.threads.max", tags=tags)
    aggregator.assert_metric("openldap.threads.max_pending", tags=tags)
    aggregator.assert_metric("openldap.uptime", tags=tags)
    aggregator.assert_metric("openldap.waiter.read", tags=tags)
    aggregator.assert_metric("openldap.waiter.write", tags=tags)
    aggregator.assert_metric("openldap.query.duration", tags=tags + ["query:stats"])
    aggregator.assert_metric("openldap.query.entries", tags=tags + ["query:stats"])
    aggregator.assert_all_metrics_covered()


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
