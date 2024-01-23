# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command('generate-metrics', short_help='Generate metrics with fake values for an integration')
@click.argument('integration')
@click.option('--api-url', default="api.datadoghq.com", help='The API URL to use, e.g. "api.datadoghq.com"')
@click.option('--api-key', required=True, help='Your API key')
@click.pass_obj
def generate_metrics(app: Application, integration: str, api_url: str, api_key: str):
    """Generate metrics with fake values for an integration

    \b
    `$ ddev meta scripts generate-metrics ray --api-url <URL> --api-key <API_KEY>`
    """

    import random
    from datetime import datetime
    from time import sleep

    from datadog_api_client import ApiClient, Configuration
    from datadog_api_client.v2.api.metrics_api import MetricsApi
    from datadog_api_client.v2.model.metric_intake_type import MetricIntakeType
    from datadog_api_client.v2.model.metric_payload import MetricPayload
    from datadog_api_client.v2.model.metric_point import MetricPoint
    from datadog_api_client.v2.model.metric_resource import MetricResource
    from datadog_api_client.v2.model.metric_series import MetricSeries
    from datadog_checks.dev.utils import get_hostname

    try:
        intg = app.repo.integrations.get(integration)
    except OSError:
        app.abort(f'Unknown target: {intg}')

    configuration = Configuration()
    configuration.request_timeout = (5, 5)
    configuration.api_key = {
        "apiKeyAuth": api_key,
    }
    # We manually set the value to allow custom URLs
    configuration.server_index = 1
    configuration.server_variables["name"] = api_url

    # Update this map to avoid generating random values for a given metric
    overriden_values = {
        'ray.worker.register_time.sum': [10, 9, 8],
    }

    with ApiClient(configuration) as api_client:
        api_instance = MetricsApi(api_client)
        loop = 0

        while True:
            series = []
            for metric in intg.metrics:
                value = (
                    overriden_values[metric.metric_name][loop % len(overriden_values[metric.metric_name])]
                    if metric.metric_name in overriden_values
                    else random.randint(0, 100)
                )
                type = (
                    MetricIntakeType.GAUGE
                    if metric.metric_type == 'gauge'
                    else MetricIntakeType.COUNT
                    if metric.metric_type == 'counter'
                    else MetricIntakeType.UNSPECIFIED
                )
                app.display_info(f"Metric {metric.metric_name} with value {value} and type {type}")

                series.append(
                    MetricSeries(
                        metric=metric.metric_name,
                        type=type,
                        points=[
                            MetricPoint(
                                timestamp=int(datetime.now().timestamp()),
                                value=value,
                            ),
                        ],
                        resources=[
                            MetricResource(
                                name=get_hostname(),
                                type="host",
                            ),
                        ],
                    )
                )
            app.display_info("Calling the API...")
            api_instance.submit_metrics(body=MetricPayload(series=series))
            app.display_info("Done.")

            app.display_info("Sleeping for 10 seconds...")
            sleep(10)
            loop += 1
