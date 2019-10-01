# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import running_on_windows_ci

windows_ci = pytest.mark.skipif(not running_on_windows_ci(), reason='Test can only be run on Windows CI')
not_windows_ci = pytest.mark.skipif(running_on_windows_ci(), reason='Test cannot be run on Windows CI')
