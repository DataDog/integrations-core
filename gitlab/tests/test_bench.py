# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.gitlab import GitlabCheck

from .common import CONFIG, LEGACY_CONFIG


@pytest.mark.usefixtures("dd_environment")
def test_legacy_run(benchmark):
    instance = LEGACY_CONFIG['instances'][0]
    c = GitlabCheck('gitlab', LEGACY_CONFIG['init_config'], instances=LEGACY_CONFIG['instances'])

    # Run once to get any initialization out of the way.
    c.check(instance)

    benchmark(c.check, instance)


@pytest.mark.usefixtures("dd_environment")
def test_run(benchmark):
    instance = CONFIG['instances'][0]
    c = GitlabCheck('gitlab', CONFIG['init_config'], instances=CONFIG['instances'])

    # Run once to get any initialization out of the way.
    c.check(instance)

    benchmark(c.check, instance)
