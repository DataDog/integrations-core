# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

from datadog_checks.marathon import Marathon

APP_METRICS = [
    'marathon.backoffFactor',
    'marathon.backoffSeconds',
    'marathon.cpus',
    'marathon.disk',
    'marathon.instances',
    'marathon.mem',
    # 'marathon.taskRateLimit', # Not present in fixture
    'marathon.tasksRunning',
    'marathon.tasksStaged',
    'marathon.tasksHealthy',
    'marathon.tasksUnhealthy',
]

Q_METRICS = [
    'marathon.queue.count',
    'marathon.queue.delay',
    'marathon.queue.offers.processed',
    'marathon.queue.offers.unused',
    'marathon.queue.offers.reject.last',
    'marathon.queue.offers.reject.launch',
]


def register_marathon_responses(
    fake_http_response: Any,
    server: str,
    *,
    apps: dict[str, Any],
    deployments: list[dict[str, Any]],
    queue: dict[str, Any],
) -> None:
    fake_http_response(f'{server}/v2/apps?embed=apps.counts', json_data=apps)
    fake_http_response(f'{server}/v2/deployments', json_data=deployments)
    fake_http_response(f'{server}/v2/queue', json_data=queue)


def test_default_configuration(aggregator, instance, apps, deployments, queue, fake_http_response):
    register_marathon_responses(
        fake_http_response,
        instance['url'],
        apps=apps,
        deployments=deployments,
        queue=queue,
    )
    check = Marathon('marathon', {}, [instance])
    check.check(instance)

    aggregator.assert_metric('marathon.apps', value=2)
    aggregator.assert_metric('marathon.deployments', value=1)
    aggregator.assert_metric('marathon.queue.size', value=2)

    for metric in APP_METRICS:
        aggregator.assert_metric(
            metric,
            count=1,
            tags=['app_id:/my-app', 'version:2016-08-25T18:13:34.079Z', 'optional:tag1', 'LABEL_NAME:label_value_1'],
        )
        aggregator.assert_metric(
            metric, count=1, tags=['app_id:/my-app-2', 'version:2016-08-25T18:13:34.079Z', 'optional:tag1']
        )

    for metric in Q_METRICS:
        aggregator.assert_metric(metric, at_least=1)


def test_empty_responses(aggregator, instance, fake_http_response):
    register_marathon_responses(
        fake_http_response,
        instance['url'],
        apps={"apps": []},
        deployments=[],
        queue={"queue": []},
    )
    check = Marathon('marathon', {}, [instance])
    check.check(instance)

    aggregator.assert_metric('marathon.apps', value=0)
    aggregator.assert_metric('marathon.queue.size', value=0)
    aggregator.assert_metric('marathon.deployments', value=0)


def test_ensure_queue_count(aggregator, apps, instance, fake_http_response):
    register_marathon_responses(
        fake_http_response,
        instance['url'],
        apps=apps,
        deployments=[],
        queue={"queue": []},
    )
    check = Marathon('marathon', {}, [instance])
    check.check(instance)

    aggregator.assert_metric('marathon.apps', value=2)
    aggregator.assert_metric('marathon.queue.size', value=0)
    aggregator.assert_metric(
        'marathon.queue.count',
        value=0,
        tags=['app_id:/my-app', 'version:2016-08-25T18:13:34.079Z', 'optional:tag1', 'LABEL_NAME:label_value_1'],
    )
    aggregator.assert_metric(
        'marathon.queue.count', value=0, tags=['app_id:/my-app-2', 'version:2016-08-25T18:13:34.079Z', 'optional:tag1']
    )
