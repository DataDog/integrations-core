# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.dev import get_here

COMPOSE_FILE = os.path.join(get_here(), 'compose', 'compose.yaml')

CONFIG = {
    "init_config": {
        "nfsiostat_path": "docker exec nfs-client /usr/sbin/nfsiostat"
    },
    "instances": [
        {"tags": ["tag1:value1"]}
    ],
}
