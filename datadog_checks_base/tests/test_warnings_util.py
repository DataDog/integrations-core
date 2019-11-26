# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import warnings

import pytest
from urllib3.exceptions import InsecureRequestWarning

from datadog_checks.base.utils.warnings_util import simplefilter

pytestmark = pytest.mark.warnings


class TestWarnings:

    def test_filters_count(self):
        initial_count = len(warnings.filters)

        for _ in range(100):
            simplefilter('default', InsecureRequestWarning)

        final_count = len(warnings.filters)

        assert final_count in (initial_count, initial_count + 1)
