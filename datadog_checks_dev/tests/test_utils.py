# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import mock


from datadog_checks.dev.utils import (
    running_on_appveyor, running_on_travis, running_on_ci
)


def test_running_on_appveyor():
    with mock.patch.dict(os.environ, {'APPVEYOR': 'true'}):
        assert running_on_appveyor() is True
        assert running_on_ci() is True


def test_running_on_travis():
    with mock.patch.dict(os.environ, {'TRAVIS': 'true'}):
        assert running_on_travis() is True
        assert running_on_ci() is True
