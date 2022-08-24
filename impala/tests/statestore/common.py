# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

TAGS = ['endpoint:http://localhost:25010/metrics_prometheus']

# "value" is only used in unit test
METRICS = [
    {
        "name": "impala.statestore.live_backends",
        "value": 2,
    },
]
