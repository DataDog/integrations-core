# -*- coding: utf-8 -*-

# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import warnings

import mock

from datadog_checks import log
from datadog_checks.base.log import init_logging


def test_get_py_loglevel():
    # default value for invalid input
    assert log._get_py_loglevel(None) == logging.INFO
    # default value for valid unicode input encoding into an invalid key
    assert log._get_py_loglevel(u'dèbùg') == logging.INFO
    # check unicode works
    assert log._get_py_loglevel(u'crit') == logging.CRITICAL
    # check string works
    assert log._get_py_loglevel('crit') == logging.CRITICAL


def test_logging_capture_warnings():

    with mock.patch('logging.Logger.warning') as log_warning:
        warnings.warn("hello-world")

        log_warning.assert_not_called()  # warnings are NOT yet captured

        init_logging()  # from here warnings are captured as logs

        warnings.warn("hello-world")
        assert log_warning.call_count == 1
        msg = log_warning.mock_calls[0].args[1]
        assert "hello-world" in msg
