# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from typing import Any, Dict, List  # noqa: F401

import yaml

from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.base.utils.common import get_docker_hostname
from datadog_checks.marklogic import MarklogicCheck

from .metrics import (
    FOREST_STATUS_TREE_CACHE_METRICS,
    GLOBAL_METRICS,
    OPTIONAL_METRICS,
    STORAGE_FOREST_METRICS,
    STORAGE_HOST_METRICS,
)

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()
PORT = 8002
MARKLOGIC_VERSION = os.environ.get('MARKLOGIC_VERSION')
API_URL = "http://{}:{}".format(HOST, PORT)
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin'
MANAGE_ADMIN_USERNAME = 'datadog_admin'
MANAGE_USER_USERNAME = 'datadog_user'
PASSWORD = 'datadog'

COMMON_TAGS = ['foo:bar']

INSTANCE = {
    'url': API_URL,
    'username': MANAGE_ADMIN_USERNAME,
    'password': PASSWORD,
    'enable_health_service_checks': True,
    'auth_type': 'digest',
    'tags': COMMON_TAGS,
}

INSTANCE_SIMPLE_USER = {
    'url': API_URL,
    'username': MANAGE_USER_USERNAME,
    'password': PASSWORD,
    'auth_type': 'digest',
    'tags': COMMON_TAGS,
}

INSTANCE_FILTERS = {
    'url': API_URL,
    'username': MANAGE_ADMIN_USERNAME,
    'password': PASSWORD,
    'auth_type': 'digest',
    'enable_health_service_checks': True,
    'tags': COMMON_TAGS,
    'resource_filters': [
        {'resource_type': 'forest', 'pattern': '^S[a-z]*'},  # Match Security and Schemas
        {'resource_type': 'forest', 'pattern': '^Sch*', 'include': False},  # Unmatch Schemas
        {'resource_type': 'database', 'pattern': '^Doc'},  # Match Documents
        {'resource_type': 'server', 'pattern': 'Admin', 'group': 'Default'},
    ],
}

CHECK_CONFIG = {
    'init_config': {},
    'instances': [INSTANCE],
}

SERVICE_CHECKS_HEALTH_TAG = {
    'database': [
        'database_name:App-Services',
        'database_name:Documents',
        'database_name:Extensions',
        'database_name:Fab',
        'database_name:Last-Login',
        'database_name:Meters',
        'database_name:Modules',
        'database_name:Schemas',
        'database_name:Security',
        'database_name:Triggers',
    ],
    'forest': [
        'forest_name:App-Services',
        'forest_name:Documents',
        'forest_name:Extensions',
        'forest_name:Fab',
        'forest_name:Last-Login',
        'forest_name:Meters',
        'forest_name:Modules',
        'forest_name:Schemas',
        'forest_name:Security',
        'forest_name:Triggers',
    ],
}


def read_fixture_file(fname):
    # type: (str) -> Dict[str, Any]
    with open(os.path.join(HERE, 'fixtures', fname)) as f:
        return yaml.safe_load(f.read())


def assert_metrics(aggregator, tags):
    # type: (AggregatorStub, List[str]) -> None
    for metric in GLOBAL_METRICS:
        aggregator.assert_metric(metric, tags=tags)
    for metric in OPTIONAL_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    # May take some time to be available
    for metric in FOREST_STATUS_TREE_CACHE_METRICS:
        aggregator.assert_metric(metric, tags=tags, at_least=0)

    storage_tag_prefixes = ['storage_path', 'marklogic_host_name', 'marklogic_host_id']
    for metric in STORAGE_HOST_METRICS:
        for tag in tags:
            aggregator.assert_metric_has_tag(metric, tag)
        for prefix in storage_tag_prefixes:
            aggregator.assert_metric_has_tag_prefix(metric, prefix)
    for metric in STORAGE_FOREST_METRICS:
        for tag in tags:
            aggregator.assert_metric_has_tag(metric, tag)
        for prefix in storage_tag_prefixes + ['forest_id', 'forest_name']:
            aggregator.assert_metric_has_tag_prefix(metric, prefix)


def assert_service_checks(aggregator, tags, count=1, include_health_checks=True):
    # type: (AggregatorStub, List[str], int, bool) -> None
    aggregator.assert_service_check('marklogic.can_connect', MarklogicCheck.OK, count=count)

    if include_health_checks:
        for database_tag in SERVICE_CHECKS_HEALTH_TAG['database']:
            aggregator.assert_service_check(
                'marklogic.database.health', MarklogicCheck.OK, tags=tags + [database_tag], count=count
            )

        for forest_tag in SERVICE_CHECKS_HEALTH_TAG['forest']:
            aggregator.assert_service_check(
                'marklogic.forest.health', MarklogicCheck.OK, tags=tags + [forest_tag], count=count
            )
