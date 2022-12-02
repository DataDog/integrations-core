# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import shutil
from copy import deepcopy

import pytest

from datadog_checks.dev import TempDir, docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.sonarqube import SonarqubeCheck

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(common.HERE, 'docker', common.COMPOSE_FILE)

    # The scanner creates artifacts within the project such as `.scannerwork/`
    with TempDir('sonarqube-project') as temp_dir:
        project_dir = os.path.join(temp_dir, 'project')
        if not os.path.isdir(project_dir):
            shutil.copytree(os.path.join(common.HERE, 'docker', 'project'), project_dir)
        with docker_run(
            compose_file,
            env_vars={'PROJECT_DIR': project_dir},
            conditions=[
                CheckDockerLogs('sonarqube', ['SonarQube is up'], attempts=100, wait=3),
                CheckDockerLogs('sonar-scanner', ['ANALYSIS SUCCESSFUL'], attempts=100, wait=3),
                CheckDockerLogs(
                    'sonarqube', ['Executed task | project=org.sonarqube:sonarqube-scanner'], attempts=100, wait=3
                ),
            ],
            mount_logs=True,
            sleep=10,
        ):
            yield common.CHECK_CONFIG, {'use_jmx': True}


@pytest.fixture
def web_instance():
    return deepcopy(common.WEB_INSTANCE)


@pytest.fixture
def web_instance_with_autodiscovery_only_include():
    return deepcopy(common.WEB_INSTANCE_WITH_AUTODISCOVERY_ONLY_INCLUDE)


@pytest.fixture
def web_instance_with_autodiscovery_include_all_and_exclude():
    return deepcopy(common.WEB_INSTANCE_WITH_AUTODISCOVERY_INCLUDE_ALL_AND_EXCLUDE)


@pytest.fixture
def web_instance_with_autodiscovery_include_all_and_limit():
    return deepcopy(common.WEB_INSTANCE_WITH_AUTODISCOVERY_INCLUDE_ALL_AND_LIMIT)


@pytest.fixture(scope='session')
def sonarqube_check():
    return lambda instance: SonarqubeCheck('sonarqube', {}, [instance])
