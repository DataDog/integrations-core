# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import shutil
from copy import deepcopy

import pytest

from datadog_checks.dev import TempDir, docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints
from datadog_checks.sonarqube import SonarqubeCheck

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(common.HERE, 'docker', 'docker-compose.yaml')

    # The scanner creates artifacts within the project such as `.scannerwork/`
    with TempDir('sonarqube-project') as temp_dir:
        project_dir = os.path.join(temp_dir, 'project')
        if not os.path.isdir(project_dir):
            shutil.copytree(os.path.join(common.HERE, 'docker', 'project'), project_dir)

        with docker_run(
            compose_file,
            service_name='sonarqube',
            env_vars={'PROJECT_DIR': project_dir},
            conditions=[
                CheckDockerLogs('sonarqube', ['SonarQube is up']),
                CheckEndpoints([common.WEB_INSTANCE['web_endpoint']]),
            ],
            mount_logs=True,
        ):
            with docker_run(
                compose_file,
                service_name='sonar-scanner',
                env_vars={'PROJECT_DIR': project_dir},
                conditions=[CheckDockerLogs('sonar-scanner', ['ANALYSIS SUCCESSFUL'], attempts=100, wait=3)],
                sleep=10,
                # Don't worry about spinning down since the outermost runner will already do that
                down=lambda: None,
            ):
                yield common.CHECK_CONFIG, {'use_jmx': True}


@pytest.fixture
def web_instance():
    return deepcopy(common.WEB_INSTANCE)


@pytest.fixture(scope='session')
def sonarqube_check():
    return lambda instance: SonarqubeCheck('sonarqube', {}, [instance])
