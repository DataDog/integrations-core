# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import running_on_appveyor


not_appveyor = pytest.mark.skipif(running_on_appveyor(), reason="Test can't be run on Appveyor")
