# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

MALFORMED_VERSION_STRING_PARAMS = [
    pytest.param('rethinkdb 2.3.3', id='no-compilation-string'),
    pytest.param('rethinkdb (GCC 4.9.2)', id='no-version'),
    pytest.param('rethinkdb', id='prefix-only'),
    pytest.param('abc 2.4.0~0bionic (GCC 4.9.2)', id='wrong-prefix'),
]
