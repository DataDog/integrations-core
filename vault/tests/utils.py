# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev.utils import get_metadata_metrics

from .common import HERE

def get_response(filename):
    metrics_file_path = os.path.join(HERE, 'fixtures', filename)
    with open(metrics_file_path, 'r') as f:
        response = f.read()
    return response


def assert_all_metrics(aggregator):
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_no_duplicate_metrics()
