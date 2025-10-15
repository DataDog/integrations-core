# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""This module contains test annotations"""

import pytest

from .utils import ON_MACOS, ON_WINDOWS

requires_windows = pytest.mark.skipif(not ON_WINDOWS, reason='Requires Windows')
requires_linux = pytest.mark.skipif(ON_MACOS or ON_WINDOWS, reason='Requires Linux')
requires_unix = pytest.mark.skipif(ON_WINDOWS, reason='Requires Linux or macOS')
