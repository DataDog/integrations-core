# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from memory_profiler import profile

from tests.common import TABULAR_OBJECTS, create_check, generate_instance_config

pytestmark = pytest.mark.usefixtures("dd_environment")


@profile
def test_memory():
    instance = generate_instance_config(TABULAR_OBJECTS)
    instance['optimize_mib_memory_usage'] = True

    check = create_check(instance)
    check.check(instance)

    check = create_check(instance)
    check.check(instance)

    check = create_check(instance)
    check.check(instance)


# for profiling with cProfile and line_profiler
import pytest
pytest.main([__file__, '--capture=no'])
