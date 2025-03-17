# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE = os.path.join(HERE, 'compose')


def get_nexus_password():
    try:
        container_id = (
            subprocess.check_output("docker ps --filter 'ancestor=sonatype/nexus3' --format '{{.ID}}'", shell=True)
            .decode()
            .strip()
        )

        if not container_id:
            print("Error: No running Nexus container found.")
            exit(1)

        password_file = "/opt/sonatype/sonatype-work/nexus3/admin.password"
        password = (
            subprocess.check_output(f"docker exec {container_id} sh -c 'cat {password_file}'", shell=True)
            .decode()
            .strip()
        )

    except subprocess.CalledProcessError:
        print("Error executing Docker commands")
        exit(1)
    return password


INSTANCE = {
    "username": "admin",
    "server_url": "http://127.0.0.1:8081",
    "min_collection_interval": 400,
    "tags": ["sample_tag:sample_value"],
}
