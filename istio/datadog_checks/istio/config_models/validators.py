# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def initialize_instance(values, **kwargs):
    if 'use_openmetrics' in values and values['use_openmetrics']:
        """
        prometheus_url is not used in OpenmetricsV2BaseCheck
        """
        values['prometheus_url'] = ""
    return values
