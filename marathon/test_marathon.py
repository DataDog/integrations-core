# (C) Datadog, Inc. 2010-2016
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

def getMetricNames(metrics):
    return [metric[0] for metric in metrics]

class MarathonCheckTest(AgentCheckTest):
    CHECK_NAME = 'marathon'

    def test_default_configuration(self):
        ci_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ci")

        def side_effect(url, timeout, auth):
            if "v2/apps" in url:
                return Fixtures.read_json_file("apps.json", sdk_dir=ci_dir)
            elif "v2/deployments" in url:
                return Fixtures.read_json_file("deployments.json", sdk_dir=ci_dir)
            else:
                raise Exception("unknown url:" + url)

        self.run_check(DEFAULT_CONFIG, mocks={"get_json": side_effect})
        self.assertMetric('marathon.apps', value=1)
        self.assertMetric('marathon.deployments', value=1)


    def test_empty_responses(self):
        def side_effect(url, timeout, auth):
            if "v2/apps" in url:
                return {"apps": []}
            elif "v2/deployments" in url:
                return {"deployments": []}
            else:
                raise Exception("unknown url:" + url)

        self.run_check(DEFAULT_CONFIG, mocks={"get_json": side_effect})
        self.assertMetric('marathon.apps', value=0)
