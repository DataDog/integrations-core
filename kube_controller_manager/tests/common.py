# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.base.utils.http_testing import MockHTTPResponse
from datadog_checks.dev import get_here

HERE = get_here()


def make_mock_metrics(mock_openmetrics_http, fixture_filename):
    f_name = os.path.join(HERE, 'fixtures', fixture_filename)
    mock_openmetrics_http.get.return_value = MockHTTPResponse(file_path=f_name, headers={'Content-Type': 'text/plain'})
    return mock_openmetrics_http
