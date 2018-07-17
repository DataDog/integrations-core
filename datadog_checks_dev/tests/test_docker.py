# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev.docker import compose_file_active, docker_run
from datadog_checks.dev.subprocess import run_command

HERE = os.path.dirname(os.path.abspath(__file__))
DOCKER_DIR = os.path.join(HERE, 'docker')


class TestComposeFileActive:
    def test_down(self):
        compose_file = os.path.join(DOCKER_DIR, 'test_default.yaml')
        run_command(['docker-compose', '-f', compose_file, 'down'], capture=True)

        assert compose_file_active(compose_file) is False

    def test_up(self):
        compose_file = os.path.join(DOCKER_DIR, 'test_default.yaml')

        try:
            run_command(['docker-compose', '-f', compose_file, 'up', '-d'], check=True)
            assert compose_file_active(compose_file) is True
        finally:
            run_command(['docker-compose', '-f', compose_file, 'down'], capture=True)


class TestDockerRun:
    def test_compose_file(self):
        compose_file = os.path.join(DOCKER_DIR, 'test_default.yaml')

        try:
            with docker_run(compose_file):
                assert compose_file_active(compose_file) is True
            assert compose_file_active(compose_file) is False
        finally:
            run_command(['docker-compose', '-f', compose_file, 'down'], capture=True)
