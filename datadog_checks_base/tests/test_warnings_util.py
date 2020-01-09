# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import warnings

import pytest
import requests
from six import PY2
from urllib3.exceptions import InsecureRequestWarning

from datadog_checks.base import ConfigurationError
from datadog_checks.base.utils.warnings_util import disable_warnings_ctx, simplefilter


def test_filters_count():
    initial_count = len(warnings.filters)

    for _ in range(100):
        simplefilter('default', InsecureRequestWarning)

    final_count = len(warnings.filters)

    assert final_count in (initial_count, initial_count + 1)


def test_filters_count_append():
    initial_count = len(warnings.filters)

    for _ in range(100):
        simplefilter('default', InsecureRequestWarning, append=1)

    final_count = len(warnings.filters)

    if PY2:
        assert final_count in (initial_count + 100, initial_count + 101)
    else:
        assert final_count in (initial_count, initial_count + 1)


def test_disable_warnings_ctx_disabled():
    with pytest.warns(None) as record:
        with disable_warnings_ctx(InsecureRequestWarning):
            requests.get('https://www.example.com', verify=False)
    assert all(not issubclass(warning.category, InsecureRequestWarning) for warning in record)

    with pytest.warns(None) as record:
        with disable_warnings_ctx(InsecureRequestWarning, disable=True):
            requests.get('https://www.example.com', verify=False)
    assert all(not issubclass(warning.category, InsecureRequestWarning) for warning in record)


def test_disable_warnings_ctx_not_disabled():
    with pytest.warns(InsecureRequestWarning):
        requests.get('https://www.example.com', verify=False)

    with pytest.warns(InsecureRequestWarning):
        with disable_warnings_ctx(InsecureRequestWarning, disable=False):
            requests.get('https://www.example.com', verify=False)

    with pytest.warns(InsecureRequestWarning):
        with disable_warnings_ctx(ConfigurationError):
            requests.get('https://www.example.com', verify=False)
