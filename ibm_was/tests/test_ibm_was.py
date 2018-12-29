# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import os

from datadog_checks.ibm_was import IbmWasCheck
from . import common


def mock_data(file):
    filepath = os.path.join(common.FIXTURE_DIR, file)
    with open(filepath, "rb") as f:
        data = f.read()
    return data


@mock.patch('datadog_checks.ibm_was.IbmWasCheck.make_request',
            return_value=mock_data("server.xml"))
def test_check(mock_server, aggregator, instance):
    check = IbmWasCheck('ibm_was', {}, {})
    check.check(instance)
