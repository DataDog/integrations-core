# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.envoy import Envoy

from ..common import SERVER_INFO_URL
from .common import INSTANCES


@pytest.mark.usefixtures('dd_environment')
def test_run(benchmark):
    instance = INSTANCES['main']
    c = Envoy('envoy', {}, [instance])

    # Run once to get logging of unknown metrics out of the way.
    c.check(instance)

    benchmark(c.check, instance)


def test_fixture(benchmark, fixture_path, serve_fixture_file):
    instance = INSTANCES['main']
    c = Envoy('envoy', {}, [instance])

    serve_fixture_file(fixture_path('legacy/multiple_services'), instance['stats_url'], SERVER_INFO_URL)

    # Run once to get logging of unknown metrics out of the way.
    c.check(instance)

    benchmark(c.check, instance)
