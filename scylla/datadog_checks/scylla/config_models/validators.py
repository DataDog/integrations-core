# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Here you can include additional config validators or transformers
from datadog_checks.base import ConfigurationError
from datadog_checks.scylla.metrics import ADDITIONAL_METRICS_MAP


def initialize_instance(values, **kwargs):
    if 'metric_groups' in values:
        errors = []
        for group in values['metric_groups']:
            try:
                ADDITIONAL_METRICS_MAP[group]
            except KeyError:
                errors.append(group)

        if errors:
            raise ConfigurationError('Invalid metric_groups found in scylla conf.yaml: {}'.format(', '.join(errors)))

    return values
