# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import os

# project
from tests.checks.common import AgentCheckTest, Fixtures

DEPLOYMENT_METRICS_CONFIG = {
    'init_config': {
        'default_timeout': 5
    },
    'instances': [
        {
            'url': 'http://localhost:8080',
            'enable_deployment_metrics': True
        }
    ]
}

DEFAULT_CONFIG = {
    'init_config': {
        'default_timeout': 5
    },
    'instances': [
        {
            'url': 'http://localhost:8080'
        }
    ]
}

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

class MarathonCheckTest(AgentCheckTest):
    CHECK_NAME = 'marathon'

    def test_default_configuration(self):
        ci_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ci")

        def side_effect(url, timeout, auth, acs_url, verify):
            if "v2/apps" in url:
                return Fixtures.read_json_file("apps.json", sdk_dir=ci_dir)
            elif "v2/deployments" in url:
                return Fixtures.read_json_file("deployments.json", sdk_dir=ci_dir)
            elif "v2/queue" in url:
                return Fixtures.read_json_file("queue.json", sdk_dir=ci_dir)
            else:
                raise Exception("unknown url:" + url)

        self.run_check(DEFAULT_CONFIG, mocks={"get_json": side_effect})
        self.assertMetric('marathon.apps', value=2)
        for metric in APP_METRICS:
            self.assertMetric(metric, count=1, tags=['app_id:/my-app', 'version:2016-08-25T18:13:34.079Z'])
            self.assertMetric(metric, count=1, tags=['app_id:/my-app-2', 'version:2016-08-25T18:13:34.079Z'])
        self.assertMetric('marathon.deployments', value=1)
        for metric in Q_METRICS:
            self.assertMetric(metric, at_least=1)

    def test_empty_responses(self):
        def side_effect(url, timeout, auth, acs_url, verify):
            if "v2/apps" in url:
                return {"apps": []}
            elif "v2/deployments" in url:
                return {"deployments": []}
            elif "v2/queue" in url:
                return {"queue": []}
            else:
                raise Exception("unknown url:" + url)

        self.run_check(DEFAULT_CONFIG, mocks={"get_json": side_effect})
        self.assertMetric('marathon.apps', value=0)
