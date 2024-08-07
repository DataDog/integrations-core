"""
This file must be named such that it comes last lexicographically.
"""

# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import sys

import pytest
from six import PY2

pytestmark = [pytest.mark.unit]


@pytest.mark.skipif(PY2, reason='BoringSSL patching only available on Python 3')
def test_use_boringssl(datadog_agent, mocker):
    import datadog_checks.base

    inject_into_urllib3 = mocker.patch('urllib3.contrib.pyopenssl.inject_into_urllib3')
    inject_into_urllib3.assert_not_called()

    # Enable the BoringSSL patching
    datadog_agent._config['use_boringssl'] = True

    # Force the module to be loaded again
    del sys.modules['datadog_checks.base']

    import datadog_checks.base  # noqa: F401, F811

    inject_into_urllib3.assert_called_once()
