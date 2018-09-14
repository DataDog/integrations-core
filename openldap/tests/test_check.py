# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import ldap3
import pytest

from datadog_checks.dev.docker import get_docker_hostname
from datadog_checks.utils.platform import Platform

pytestmark = pytest.mark.integration


@pytest.fixture
def instance():
    return {
        "url": "ldap://{}:3890".format(get_docker_hostname()),
        "username": "cn=monitor,dc=example,dc=org",
        "password": "monitor",
        "custom_queries": [{
            "name": "stats",
            "search_base": "cn=statistics,cn=monitor",
            "search_filter": "(!(cn=Statistics))",
        }],
        "tags": ["test:integration"]
    }


@pytest.fixture
def instance_ssl(instance):
    instance["url"] = "ldaps://{}:6360".format(get_docker_hostname())
    return instance


def test_check(aggregator, check, openldap_server, instance):
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


def test_check_ssl(aggregator, check, openldap_server, instance_ssl):
    tags = ["url:{}".format(instance_ssl["url"]), "test:integration"]
    # Should fail certificate verification
    with pytest.raises(ldap3.core.exceptions.LDAPSocketOpenError):
        check.check(instance_ssl)
    instance_ssl["ssl_verify"] = False
    # Should work now
    check.check(instance_ssl)
    aggregator.assert_service_check("openldap.can_connect", check.OK, tags=tags)


@pytest.mark.skipif(not Platform.is_linux(), reason='Windows sockets are not file handles')
def test_check_socket(aggregator, check, openldap_server, instance):
    instance["url"] = "ldapi://{}".format(openldap_server)
    tags = ["url:{}".format(instance["url"]), "test:integration"]
    check.check(instance)
    aggregator.assert_service_check("openldap.can_connect", check.OK, tags=tags)
