# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import ON_MACOS, ON_WINDOWS

requires_linux = pytest.mark.skipif(ON_MACOS or ON_WINDOWS, reason='Requires Linux')
requires_unix = pytest.mark.skipif(ON_WINDOWS, reason='Requires Linux or macOS')
requires_windows = pytest.mark.skipif(not ON_WINDOWS, reason='Requires Windows')
