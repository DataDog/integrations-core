# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import re


def initialize_instance(values, **kwargs):
    if 'prometheus_plugin' in values:
        plugin_settings = values['prometheus_plugin']
        if 'url' not in plugin_settings:
            raise ValueError("'prometheus_plugin.url' field is required.")
        if not re.match(r"https?:\/\/", plugin_settings['url']):
            raise ValueError("'prometheus_plugin.url' field must be an HTTP or HTTPS URL.")
        if 'unaggregated_endpoint' in plugin_settings:
            unagg_ep = plugin_settings['unaggregated_endpoint']
            if not re.match(r'(per-object|detailed(\?.+)?)$', unagg_ep):
                raise ValueError(
                    "'prometheus_plugin.unaggregated_endpoint' must be 'per-object', 'detailed', "
                    "or 'detailed?<QUERY>'."
                )
        if 'include_aggregated_endpoint' in plugin_settings:
            agg_ep = plugin_settings['include_aggregated_endpoint']
            if not isinstance(agg_ep, bool):
                raise TypeError("'prometheus_plugin.include_aggregated_endpoint' must be a boolean.")
            if not agg_ep and 'unaggregated_endpoint' not in plugin_settings:
                raise ValueError(
                    "'prometheus_plugin.include_aggregated_endpoint' field should "
                    + "be set to 'true' when 'prometheus_plugin.unaggregated_endpoint' is not collected."
                )

    return values
