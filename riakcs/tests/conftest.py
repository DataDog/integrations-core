# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
import mock

from datadog_checks.riakcs import RiakCs

from . import common


@pytest.fixture
def mocked_check():
    check = RiakCs(common.CHECK_NAME, None, {}, [{}])
    check._connect = mock.Mock(return_value=(None, None, ["aggregation_key:localhost:8080"], []))

    file_contents = common.read_fixture('riakcs_in.json')

    check._get_stats = mock.Mock(return_value=check.load_json(file_contents))
    return check


@pytest.fixture
def check():
    return RiakCs(common.CHECK_NAME, None, {}, [{}])


@pytest.fixture
def mocked_check21():
    check = RiakCs(common.CHECK_NAME, None, {}, [{}])
    check._connect = mock.Mock(return_value=(
        None,
        None,
        ["aggregation_key:localhost:8080"],
        common.CONFIG_21["metrics"],
    ))

    file_contents = common.read_fixture('riakcs21_in.json')

    check._get_stats = mock.Mock(return_value=check.load_json(file_contents))
    return check
