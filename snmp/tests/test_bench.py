# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .common import TABULAR_OBJECTS, generate_instance_config


def test_tabular_enforce(benchmark, check):
    instance = generate_instance_config(TABULAR_OBJECTS)

    benchmark(check.check, instance)


def test_tabular_no_enforce(benchmark, check):
    instance = generate_instance_config(TABULAR_OBJECTS)
    instance["enforce_mib_constraints"] = False

    benchmark(check.check, instance)
