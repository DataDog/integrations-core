# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.vault import Vault

from .common import INSTANCES


@pytest.mark.usefixtures('dd_environment')
def test_run(benchmark):
    instance = INSTANCES['main']
    c = Vault('vault', {}, [instance])

    # Run once to get instantiation of config out of the way.
    c.check(instance)

    benchmark(c.check, instance)
