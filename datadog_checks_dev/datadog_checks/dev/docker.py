# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from six.moves.urllib.parse import urlparse

from .utils import run_command


def get_docker_hostname():
    return urlparse(os.getenv('DOCKER_HOST', '')).hostname or 'localhost'


def get_container_ip(container_id_or_name):
    """Get a Docker container's IP address from its id or name."""
    command = [
        'docker',
        'inspect',
        '-f',
        '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}',
        container_id_or_name
    ]

    return run_command(command, capture='out').stdout.strip()
