# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import running_on_windows_ci

not_windows_ci = pytest.mark.skipif(running_on_windows_ci(), reason='Test cannot be run on Windows CI')
