# -*- coding: utf-8 -*-

# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

from datadog_checks import log


def test_get_py_loglevel():
    # default value for invalid input
    assert log._get_py_loglevel(None) == logging.INFO
    # default value for valid unicode input encoding into an invalid key
    assert log._get_py_loglevel(u'dèbùg') == logging.INFO
    # check unicode works
    assert log._get_py_loglevel(u'crit') == logging.CRITICAL
    # check string works
    assert log._get_py_loglevel('crit') == logging.CRITICAL
