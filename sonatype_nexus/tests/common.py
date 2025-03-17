# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import time

from datadog_checks.dev import run_command

HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE = os.path.join(HERE, 'compose')


def get_nexus_password(max_retries=5, retry_interval=10):
    try:
        run_command("docker run -d -p 8081:8081 --name sonatype_nexus_1 sonatype/nexus3")
    except Exception as e:
        print(f"Note: {e}")

    container_id = None
    for attempt in range(max_retries):
        try:
            container_id = run_command(
                "docker ps --filter 'ancestor=sonatype/nexus3' --format '{{.ID}}'", capture=True
            ).stdout.strip()

            if container_id:
                print(f"Found Nexus container with ID: {container_id}")
                break

            print(f"Waiting for Nexus container to start... (attempt {attempt+1}/{max_retries})")
            time.sleep(retry_interval)

        except Exception as e:
            print(f"Error checking container status: {e}")
            time.sleep(retry_interval)

    if not container_id:
        print("Error: No running Nexus container found after maximum retry attempts.")
        exit(1)

    password = None
    time.sleep(45)
    for attempt in range(max_retries):
        try:
            password_file = "/opt/sonatype/sonatype-work/nexus3/admin.password"
            password = run_command(
                f"docker exec {container_id} sh -c 'cat {password_file}'", capture=True
            ).stdout.strip()

            if password:
                break

        except Exception as e:
            print(f"Password file not ready yet (attempt {attempt+1}/{max_retries}): {e}")
            time.sleep(retry_interval)

    if not password:
        print("Error: Could not retrieve Nexus password after maximum retry attempts.")
        exit(1)

    return password


INSTANCE = {
    "username": "admin",
    "server_url": "http://127.0.0.1:8081",
    "min_collection_interval": 400,
    "tags": ["sample_tag:sample_value"],
}
