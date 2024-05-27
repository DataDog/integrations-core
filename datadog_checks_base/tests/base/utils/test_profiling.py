# -*- coding: utf-8 -*-
# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import os

from datadog_checks.base.utils.profiling import PROFILING


@mock.patch("datadog_checks.base.utils.profiling.PROFILING._profiler")
def test_start(_profiler):
    PROFILING.start()
    assert PROFILING.status() == "running"
    _profiler.start.assert_called_once()

    PROFILING.start()
    _profiler.assert_not_called()

    # Ensure profiler is stopped
    PROFILING.stop()


@mock.patch("datadog_checks.base.utils.profiling.PROFILING._profiler")
def test_stop(_profiler):
    assert PROFILING.status() == "stopped"
    PROFILING.stop()
    _profiler.assert_not_called()

    PROFILING.start()
    PROFILING.stop()
    _profiler.stop.assert_called_once()

    # Ensure profiler is stopped
    PROFILING.stop()
