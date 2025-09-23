# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import copy

import mock
import pytest

from datadog_checks.riakcs import RiakCs

from . import common


@pytest.fixture
def mocked_check():
    check = RiakCs(common.CHECK_NAME, None, {}, [{}])

    file_contents = common.read_fixture('riakcs_in.json')
    check.connect_stats_getter = mock.Mock(return_value=mock.Mock(return_value=file_contents))

    return check


@pytest.fixture
def instance():
    return copy.deepcopy(common.CONFIG)


@pytest.fixture
def instance21():
    return copy.deepcopy(common.CONFIG_21)


@pytest.fixture
def check():
    return RiakCs(common.CHECK_NAME, None, {}, [{}])


@pytest.fixture
def mocked_check21():
    check = RiakCs(common.CHECK_NAME, None, {}, [{}])

    file_contents = common.read_fixture('riakcs21_in.json')
    check.connect_stats_getter = mock.Mock(return_value=mock.Mock(return_value=file_contents))

    return check
