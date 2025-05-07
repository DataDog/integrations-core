# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import time
from copy import deepcopy

import pytest

from datadog_checks.dev import docker_run, run_command

from .common import COMPOSE, INSTANCE

instance = {
    "username": "test_username",
    "password": "test_password",
    "min_collection_interval": 400,
    "server_url": "https://example.com",
}


def get_nexus_password(max_retries=5, retry_interval=10, password_wait_retries=30, password_wait_interval=10):
    try:
        run_command("docker run -d -p 8081:8081 --name sonatype_nexus_38 sonatype/nexus3:3.79.0")
    except Exception as e:
        print(f"Note: {e}")

    container_id = None
    for attempt in range(max_retries):
        try:
            container_id = run_command(
                "docker ps --filter 'ancestor=sonatype/nexus3:3.79.0' --format '{{.ID}}'", capture=True
            ).stdout.strip()

            if container_id:
                print(f"Found Nexus container with ID: {container_id}")
                break

            print(f"Waiting for Nexus container to start... (attempt {attempt + 1}/{max_retries})")
            time.sleep(retry_interval)

        except Exception as e:
            print(f"Error checking container status: {e}")
            time.sleep(retry_interval)

    if not container_id:
        print("Error: No running Nexus container found after maximum retry attempts.")
        exit(1)

    password = None
    for attempt in range(password_wait_retries):
        try:
            file_check = run_command(
                f"docker exec {container_id} sh -c '"
                "[ -f /opt/sonatype/sonatype-work/nexus3/admin.password ] "
                "&& echo \"exists\" || echo \"not exists\"'",
                capture=True,
            ).stdout.strip()

            if file_check == "exists":
                password = run_command(
                    f"docker exec {container_id} sh -c 'cat /opt/sonatype/sonatype-work/nexus3/admin.password'",
                    capture=True,
                ).stdout.strip()

                if password:
                    print(f"Successfully retrieved password after {attempt + 1} attempts")
                    break

            print(f"Password file not ready yet (attempt {attempt + 1}/{password_wait_retries})")
            time.sleep(password_wait_interval)

        except Exception as e:
            print(f"Error checking password file (attempt {attempt + 1}/{password_wait_retries}): {e}")
            time.sleep(password_wait_interval)

    if not password:
        print("Error: Could not retrieve Nexus password after maximum retry attempts.")
        exit(1)

    return password


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(COMPOSE, 'docker-compose.yaml')

    with docker_run(
        compose_file,
        build=True,
        sleep=30,
    ):
        password = get_nexus_password()
        modified_instance = deepcopy(INSTANCE)
        modified_instance["password"] = password
        yield modified_instance
