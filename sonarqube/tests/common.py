# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here, load_jmx_config

HERE = get_here()
HOST = get_docker_hostname()
PORT = 9000
PROJECT = 'org.sonarqube:sonarqube-scanner'
JMX_WEB_INSTANCE = {'host': HOST, 'port': 10443, 'is_jmx': True}
JMX_CE_INSTANCE = {'host': HOST, 'port': 10444, 'is_jmx': True}
WEB_INSTANCE_WITH_COMPONENTS = {
    'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
    'components': {PROJECT: {'tag': 'project'}},
    'tags': ['foo:bar'],
}
WEB_INSTANCE_WITH_PROJECTS = {
    'web_endpoint': 'http://{}:{}'.format(HOST, PORT),
    'projects': {'key': [{PROJECT: {'tag': 'project'}}]},
    'tags': ['foo:bar'],
}

COMPOSE_FILE = os.getenv('COMPOSE_FILE')

CHECK_CONFIG_WITH_COMPONENTS = load_jmx_config()
CHECK_CONFIG_WITH_COMPONENTS['instances'] = [JMX_WEB_INSTANCE, JMX_CE_INSTANCE, WEB_INSTANCE_WITH_COMPONENTS]
CHECK_CONFIG_WITH_PROJECTS = load_jmx_config()
CHECK_CONFIG_WITH_PROJECTS['instances'] = [JMX_WEB_INSTANCE, JMX_CE_INSTANCE, WEB_INSTANCE_WITH_PROJECTS]

METRICS = [
    'category1.metric1',
    'category1.metric2',
    'category1.metric3',
    'category1.new_metric1',
    'category2.metric4',
    'category2.metric5',
    'category2.new_metric2',
    'category3.metric6',
    'category3.metric7',
    'category3.metric8',
    'category3.metric9',
]
