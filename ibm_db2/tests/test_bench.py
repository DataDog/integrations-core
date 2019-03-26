# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.ibm_db2 import IbmDb2Check


@pytest.mark.usefixtures('dd_environment')
def test_run(benchmark, instance):
    c = IbmDb2Check('ibm_db2', {}, [instance])

    # Run once to get the initial connection out of the way.
    c.check(instance)

    benchmark(c.check, instance)
