# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock


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
    'marathon.tasksUnhealthy'
]

Q_METRICS = [
    'marathon.queue.count',
    'marathon.queue.delay',
    'marathon.queue.offers.processed',
    'marathon.queue.offers.unused',
    'marathon.queue.offers.reject.last',
    'marathon.queue.offers.reject.launch',
]


def test_default_configuration(aggregator, check, instance, apps, deployments, queue, groups):
    def side_effect(url, timeout, auth, acs_url, verify, tags):
        if "v2/apps" in url:
            return apps
        elif "v2/deployments" in url:
            return deployments
        elif "v2/queue" in url:
            return queue
        elif "v2/groups" in url:
            return groups
        else:
            raise Exception("unknown url:" + url)

    check.get_json = mock.MagicMock(side_effect=side_effect)
    check.check(instance)

    aggregator.assert_metric('marathon.apps', value=2)
    aggregator.assert_metric('marathon.deployments', value=1)
    aggregator.assert_metric('marathon.queue.size', value=2)

    for metric in APP_METRICS:
        aggregator.assert_metric(metric, count=1, tags=['app_id:/my-app', 'version:2016-08-25T18:13:34.079Z',
                                                        'optional:tag1', 'LABEL_NAME:label_value_1'])
        aggregator.assert_metric(metric, count=1, tags=['app_id:/my-app-2', 'version:2016-08-25T18:13:34.079Z',
                                                        'optional:tag1'])

    for metric in Q_METRICS:
        aggregator.assert_metric(metric, at_least=1)


def test_empty_responses(aggregator, check, instance):
    def side_effect(url, timeout, auth, acs_url, verify, tags):
        if "v2/apps" in url:
            return {"apps": []}
        elif "v2/deployments" in url:
            return []
        elif "v2/queue" in url:
            return {"queue": []}
        elif "v2/groups" in url:
            return {"apps": []}
        else:
            raise Exception("unknown url:" + url)

    check.get_json = mock.MagicMock(side_effect=side_effect)
    check.check(instance)

    aggregator.assert_metric('marathon.apps', value=0)
    aggregator.assert_metric('marathon.queue.size', value=0)
    aggregator.assert_metric('marathon.deployments', value=0)


def test_ensure_queue_count(aggregator, apps, check, instance):
    def side_effect(url, timeout, auth, acs_url, verify, tags):
        if "v2/apps" in url:
            return apps
        elif "v2/deployments" in url:
            return []
        elif "v2/queue" in url:
            return {"queue": []}
        elif "v2/groups" in url:
            return {"apps": []}
        else:
            raise Exception("unknown url:" + url)

    check.get_json = mock.MagicMock(side_effect=side_effect)
    check.check(instance)

    aggregator.assert_metric('marathon.apps', value=2)
    aggregator.assert_metric('marathon.queue.size', value=0)
    aggregator.assert_metric('marathon.queue.count', value=0, tags=['app_id:/my-app',
                                                                    'version:2016-08-25T18:13:34.079Z',
                                                                    'optional:tag1',
                                                                    'LABEL_NAME:label_value_1'])
    aggregator.assert_metric('marathon.queue.count', value=0, tags=['app_id:/my-app-2',
                                                                    'version:2016-08-25T18:13:34.079Z',
                                                                    'optional:tag1'])
