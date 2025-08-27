# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Here you can include additional config validators or transformers


def initialize_instance(values, **kwargs):
    """
    Normalize instances to support both field names.
    Parse prometheus_url first, if not available, fall back to openmetrics_endpoint.
    """
    # Map openmetrics_endpoint to prometheus_url if prometheus_url is not present
    if 'openmetrics_endpoint' in values and 'prometheus_url' not in values:
        values['prometheus_url'] = values['openmetrics_endpoint']

    # Ensure at least one endpoint is provided
    if not values.get('prometheus_url') and not values.get('openmetrics_endpoint'):
        raise ValueError('Field `openmetrics_endpoint` or `prometheus_url` must be set')

    return values
