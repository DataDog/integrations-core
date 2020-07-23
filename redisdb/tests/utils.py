# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .common import REDIS_VERSION

requires_static_version = pytest.mark.skipif(
    REDIS_VERSION == 'latest', reason='Version `latest` is ever-changing, skipping'
)
