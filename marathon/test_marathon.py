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
        self.assertMetric('marathon.apps', value=1)
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
