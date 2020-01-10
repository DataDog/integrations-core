# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.scylla import ScyllaCheck

from .common import INSTANCE_DEFAULT_METRICS, MANAGER_DEFAULT_METRICS


def test_instance_check(aggregator, db_instance, mock_db_data):
    c = ScyllaCheck('scylla', {}, [db_instance])

    c.check(db_instance)

    #from IPython.core.debugger import set_trace; set_trace()
    #import pickle
    #with open('aggregator.pcl', 'wb') as f:
    #    pickle.dump(aggregator, f)

    for m in INSTANCE_DEFAULT_METRICS:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()


# def test_manager_check(aggregator, manager_instance, mock_manager_data):
#     c = ScyllaCheck('scylla', {}, [manager_instance])
#
#     c.check(manager_instance)
#     for m in MANAGER_DEFAULT_METRICS:
#         aggregator.assert_metric(m)
#     aggregator.assert_all_metrics_covered()
