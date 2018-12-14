# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()

DEFAULT_INSTANCE = {
    'url': 'ldap://{}:3890'.format(HOST),
    'username': 'cn=monitor,dc=example,dc=org',
    'password': 'monitor',
    'custom_queries': [{
        'name': 'stats',
        'search_base': 'cn=statistics,cn=monitor',
        'search_filter': '(!(cn=Statistics))',
    }],
    'tags': ['test:integration']
}
