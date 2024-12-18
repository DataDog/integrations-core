# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.aws_neuron.metrics import METRIC_MAP, RENAME_LABELS_MAP
from datadog_checks.base import OpenMetricsBaseCheckV2


class AwsNeuronCheck(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'aws_neuron'

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances=None):

        super(AwsNeuronCheck, self).__init__(
            name,
            init_config,
            instances,
        )

    def get_default_config(self):
        return {
            'metrics': [METRIC_MAP],
            'rename_labels': RENAME_LABELS_MAP,
        }
