# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.gitlab import GitlabCheck
from .common import CONFIG


def test_run(benchmark):
    instance = CONFIG['instances'][0]
    c = GitlabCheck('gitlab', CONFIG['init_config'], {}, instances=CONFIG['instances'])

    # Run once to get any initialization out of the way.
    c.check(instance)

    benchmark(c.check, instance)
