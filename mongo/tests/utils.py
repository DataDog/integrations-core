# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os

from .common import HERE


def assert_metrics(internal_resource_tags, aggregator, metrics_categories, additional_tags=None):
    if additional_tags is None:
        additional_tags = []
    for cat in metrics_categories:
        with open(os.path.join(HERE, "results", f"metrics-{cat}.json"), 'r') as f:
            for metric in json.load(f):
                aggregator.assert_metric(
                    metric['name'],
                    value=metric['value'],
                    count=1,
                    tags=additional_tags + metric['tags'] + internal_resource_tags,
                    metric_type=metric['type'],
                )


def run_check_once(mongo_check, dd_run_check, cancel=True):
    dd_run_check(mongo_check)
    if cancel:
        mongo_check.cancel()
    if mongo_check._slow_operations._job_loop_future is not None:
        mongo_check._slow_operations._job_loop_future.result()
    if mongo_check._operation_samples._job_loop_future is not None:
        mongo_check._operation_samples._job_loop_future.result()
