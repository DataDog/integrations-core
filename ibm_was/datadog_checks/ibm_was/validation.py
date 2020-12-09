# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import ConfigurationError

REQUIRED_QUERY_FIELDS = ['stat', 'metric_prefix']


def validate_query(query):
    for field in REQUIRED_QUERY_FIELDS:
        if field not in query:
            raise ConfigurationError("Custom Query: {} missing required field: {}. Skipping".format(query, field))
