# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here

STRIMZI_VERSION = os.environ["STRIMZI_VERSION"]
HERE = get_here()

MOCKED_CLUSTER_OPERATOR_INSTANCE = {'cluster_operator_endpoint': 'http://cluster-operator:8080/metrics'}

MOCKED_TOPIC_OPERATOR_INSTANCE = {'topic_operator_endpoint': 'http://entity-operator:8080/metrics'}

MOCKED_USER_OPERATOR_INSTANCE = {'user_operator_endpoint': 'http://entity-operator:8081/metrics'}

MOCKED_CLUSTER_OPERATOR_TAGS = {
    f'endpoint:{MOCKED_CLUSTER_OPERATOR_INSTANCE["cluster_operator_endpoint"]}',
}

MOCKED_TOPIC_OPERATOR_TAGS = {
    f'endpoint:{MOCKED_TOPIC_OPERATOR_INSTANCE["topic_operator_endpoint"]}',
}

MOCKED_USER_OPERATOR_TAGS = {
    f'endpoint:{MOCKED_USER_OPERATOR_INSTANCE["user_operator_endpoint"]}',
}

CLUSTER_OPERATOR_METRICS = (
    {
        "name": "strimzi.cluster_operator.jvm.gc.memory_promoted_bytes.count",
        "value": 1,
    },
)

TOPIC_OPERATOR_METRICS = (
    {
        "name": "strimzi.topic_operator.jvm.gc.memory_promoted_bytes.count",
        "value": 2,
    },
)

USER_OPERATOR_METRICS = (
    {
        "name": "strimzi.user_operator.jvm.gc.memory_promoted_bytes.count",
        "value": 3,
    },
)
