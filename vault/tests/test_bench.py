# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.vault import Vault
from .common import INSTANCES


def test_run(benchmark):
    instance = INSTANCES['main']
    c = Vault('vault', None, {}, [instance])

    # Run once to get instantiation of config out of the way.
    c.check(instance)

    benchmark(c.check, instance)
