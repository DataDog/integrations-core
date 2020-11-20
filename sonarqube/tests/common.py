# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev import get_docker_hostname, get_here, load_jmx_config

HERE = get_here()
HOST = get_docker_hostname()
PROJECT = 'org.sonarqube:sonarqube-scanner'
SERVER_INSTANCE = {'host': HOST, 'port': 10443, 'is_jmx': True}
WEB_INSTANCE = {
    'web_endpoint': 'http://{}:9000'.format(HOST),
    'components': {PROJECT: {'tag': 'project'}},
    'tags': ['foo:bar'],
}

CHECK_CONFIG = load_jmx_config()
CHECK_CONFIG['instances'] = [SERVER_INSTANCE, WEB_INSTANCE]
