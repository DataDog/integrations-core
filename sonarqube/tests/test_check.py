# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from .common import PROJECT
from .metrics import WEB_METRICS

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def test_check(aggregator, dd_run_check, sonarqube_check, web_instance):
    check = sonarqube_check(web_instance)
    dd_run_check(check)

    global_tags = ['endpoint:{}'.format(web_instance['web_endpoint'])]
    global_tags.extend(web_instance['tags'])

    project_tag = 'project:{}'.format(PROJECT)
    for metric in WEB_METRICS:
        tags = [project_tag]
        tags.extend(global_tags)
        aggregator.assert_metric(metric, tags=tags)

    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_check_with_autodiscovery(
    aggregator, dd_run_check, sonarqube_check, web_instance_with_autodiscovery_only_include
):
    check = sonarqube_check(web_instance_with_autodiscovery_only_include)
    dd_run_check(check)

    global_tags = ['endpoint:{}'.format(web_instance_with_autodiscovery_only_include['web_endpoint'])]
    global_tags.extend(web_instance_with_autodiscovery_only_include['tags'])

    project_tag = 'project:{}'.format(PROJECT)
    for metric in WEB_METRICS:
        tags = [project_tag]
        tags.extend(global_tags)
        aggregator.assert_metric(metric, tags=tags)

    aggregator.assert_service_check('sonarqube.api_access', status=check.OK, tags=global_tags)


def test_version_metadata(datadog_agent, dd_run_check, sonarqube_check, web_instance):
    check = sonarqube_check(web_instance)
    check.check_id = 'test:123'

    version_data = [str(part) for part in os.environ['SONARQUBE_VERSION'].split('.')]
    version_parts = {'version.{}'.format(name): part for name, part in zip(('major', 'minor', 'patch'), version_data)}
    version_parts['version.scheme'] = 'semver'

    dd_run_check(check)
    datadog_agent.assert_metadata('test:123', version_parts)
