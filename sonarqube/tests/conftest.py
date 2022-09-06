# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import shutil
import time
from copy import deepcopy

import pytest

from datadog_checks.dev import TempDir, docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints, WaitForPortListening
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
            service_name='sonarqube',
            env_vars={'PROJECT_DIR': project_dir},
            conditions=[
                CheckDockerLogs('sonarqube', ['SonarQube is up'], attempts=100, wait=3),
                CheckEndpoints([common.WEB_INSTANCE['web_endpoint']]),
                WaitForPortListening(common.HOST, common.PORT),
            ],
            mount_logs=True,
        ):
            # Wait a bit for the listener be ready
            time.sleep(5)
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
