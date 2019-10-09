# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .common import POSTGRES_VERSION

requires_over_10 = pytest.mark.skipif(float(POSTGRES_VERSION) < 10, reason='This test is for over 10 only')
