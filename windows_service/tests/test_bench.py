# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.windows_service import WindowsService


def test_run(benchmark, instance_all):
    check = WindowsService('windows_service', {}, [instance_all])

    # Run once to get any set up out of the way.
    check.check(instance_all)

    benchmark(check.check, instance_all)


def test_all_startup_type_tag(benchmark, instance_all):
    instance_all['windows_service_startup_type_tag'] = True
    check = WindowsService('windows_service', {}, [instance_all])

    # Run once to get any set up out of the way.
    check.check(instance_all)

    benchmark(check.check, instance_all)
