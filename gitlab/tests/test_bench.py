# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

pytestmark = [pytest.mark.usefixtures('dd_environment')]


def test_legacy_run(benchmark, dd_run_check, gitlab_check, legacy_config):
    check = gitlab_check(legacy_config)

    # Run once to get any initialization out of the way.
    dd_run_check(check)

    benchmark(check.check, None)


@pytest.mark.parametrize('use_openmetrics', [True, False], indirect=True)
def test_run(benchmark, dd_run_check, gitlab_check, get_config, use_openmetrics):
    check = gitlab_check(get_config(use_openmetrics))

    # Run once to get any initialization out of the way.
    dd_run_check(check)

    benchmark(check.check, None)
