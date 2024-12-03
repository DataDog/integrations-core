# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import subprocess
from copy import deepcopy
from random import random

import pytest
import requests

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import WaitFor

from .common import HERE, PROXMOX_URL


def wait_for_proxmox():
    try:
        res_open = requests.get(PROXMOX_URL, verify=False)
        res_open.raise_for_status()
    except Exception:
        return False
    else:
        return res_open.status_code == 200


@pytest.fixture(scope='session')
def dd_environment(dd_save_state):
    with docker_run(
        compose_file=os.path.join(HERE, 'compose', 'docker-compose.yaml'),
        conditions=[WaitFor(wait_for_proxmox)],
    ):
        r = subprocess.run(
            [
                'docker',
                'exec',
                'pve',
                'pveum',
                'user',
                'token',
                'add',
                'root@pam',
                f"dd-agent-{str(random())[2:]}",
                '--privsep',
                'false',
                "--output-format",
                "json",
            ],
            capture_output=True,
            text=True,
        )

        r_json = json.loads(r.stdout)
        dd_save_state('proxmox_instance', {'token_id': r_json['full-tokenid'], 'token_secret': r_json['value']})
        yield {}


@pytest.fixture
def instance(dd_get_state):
    return deepcopy(dd_get_state('proxmox_instance', default={}))
