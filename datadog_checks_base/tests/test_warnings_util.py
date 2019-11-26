# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import warnings

import pytest
import requests
from urllib3.exceptions import InsecureRequestWarning

from datadog_checks.base.utils.warnings_util import disable_warnings_ctx, simplefilter

pytestmark = pytest.mark.warnings


def test_filters_count():
    initial_count = len(warnings.filters)

    for _ in range(100):
        simplefilter('default', InsecureRequestWarning)

    final_count = len(warnings.filters)

    assert final_count in (initial_count, initial_count + 1)


def test_disable_warnings_ctx_disabled():

    with disable_warnings_ctx(InsecureRequestWarning):
        with pytest.warns(None):
            requests.get('https://www.example.com')

    with disable_warnings_ctx(InsecureRequestWarning, disable=True):
        with pytest.warns(None):
            requests.get('https://www.example.com')


def test_disable_warnings_ctx_not_disabled():
    with pytest.warns(InsecureRequestWarning):
        requests.get('https://www.example.com', verify=False)

    with disable_warnings_ctx(InsecureRequestWarning, disable=False):
        with pytest.warns(InsecureRequestWarning):
            requests.get('https://www.example.com', verify=False)
