# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.tooling.release import get_package_name, get_folder_name


def test_get_package_name():
    assert get_package_name('datadog_checks_base') == 'datadog-checks-base'
    assert get_package_name('my_check') == 'datadog-my-check'


def test_get_folder_name():
    assert get_folder_name('datadog-checks-base') == 'datadog_checks_base'
    assert get_folder_name('datadog-my-check') == 'my_check'
