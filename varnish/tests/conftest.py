# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
import os
import subprocess
import time

from . import common


@pytest.fixture(scope="session")
def spin_up_varnish():
    env = os.environ
    target = "varnish{}".format(env["VARNISH_VERSION"].split(".")[0])
    args = [
        "docker-compose",
        "-f", os.path.join(common.HERE, 'compose', 'docker-compose.yaml')
    ]
    subprocess.check_call(args + ["down"], env=env)
    subprocess.check_call(args + ["up", "-d", target], env=env)
    time.sleep(2)
    yield
    subprocess.check_call(args + ["down"], env=env)
