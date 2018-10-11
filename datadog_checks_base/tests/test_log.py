# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks import log


def test_get_py_loglevel():
    """
    Ensure function _get_py_loglevel is exposed
    """
    assert getattr(log, "_get_py_loglevel")
