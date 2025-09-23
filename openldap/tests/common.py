# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()

DEFAULT_INSTANCE = {
    'url': 'ldap://{}:1389'.format(HOST),
    'username': 'cn=admin,dc=example,dc=org',
    'password': 'adminpassword',
    'custom_queries': [
        {'name': 'stats', 'search_base': 'cn=statistics,cn=monitor', 'search_filter': '(!(cn=Statistics))'}
    ],
    'tags': ['test:integration'],
}


def _check(aggregator, check, tags):
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
