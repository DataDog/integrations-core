# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# 3p
from nose.plugins.attrib import attr

# project
from checks import AgentCheck
from tests.checks.common import AgentCheckTest

# sample from /status?json
#  {
#     "accepted conn": 350,
#     "active processes": 1,
#     "idle processes": 2,
#     "listen queue": 0,
#     "listen queue len": 0,
#     "max active processes": 2,
#     "max children reached": 0,
#     "max listen queue": 0,
#     "pool": "www",
#     "process manager": "dynamic",
#     "slow requests": 0,
#     "start since": 4758,
#     "start time": 1426601833,
#     "total processes": 3
# }


@attr(requires='php_fpm')
class PHPFPMCheckTest(AgentCheckTest):
    CHECK_NAME = 'php_fpm'

    def test_bad_status(self):
        instance = {
            'status_url': 'http://localhost:9001/fpm_status',
            'tags': ['expectedbroken']
        }

        self.assertRaises(Exception, self.run_check, {'instances': [instance]})

    def test_bad_ping(self):
        instance = {
            'ping_url': 'http://localhost:9001/fpm_status',
            'tags': ['expectedbroken']
        }

        self.run_check({'instances': [instance]})
        self.assertServiceCheck(
            'php_fpm.can_ping',
            status=AgentCheck.CRITICAL,
            tags=['ping_url:http://localhost:9001/fpm_status', 'expectedbroken'],
            count=1
        )

        self.coverage_report()

    def test_bad_ping_reply(self):
        instance = {
            'ping_url': 'http://localhost:181/ping',
            'ping_reply': 'blah',
            'tags': ['expectedbroken']
        }

        self.run_check({'instances': [instance]})
        self.assertServiceCheck(
            'php_fpm.can_ping',
            status=AgentCheck.CRITICAL,
            tags=['ping_url:http://localhost:181/ping', 'expectedbroken'],
            count=1
        )

        self.coverage_report()

    def test_status(self):
        instance = {
            'status_url': 'http://localhost:181/fpm_status',
            'ping_url': 'http://localhost:181/ping',
            'tags': ['cluster:forums']
        }

        self.run_check_twice({'instances': [instance]})

        metrics = [
            'php_fpm.listen_queue.size',
            'php_fpm.processes.idle',
            'php_fpm.processes.active',
            'php_fpm.processes.total',
            'php_fpm.requests.slow',
            'php_fpm.requests.accepted',
        ]

        expected_tags = ['cluster:forums', 'pool:www']

        for mname in metrics:
            self.assertMetric(mname, count=1, tags=expected_tags)

        self.assertServiceCheck('php_fpm.can_ping', status=AgentCheck.OK,
                                count=1,
                                tags=['ping_url:http://localhost:181/ping',
                                      'cluster:forums'])

        self.assertMetric('php_fpm.processes.max_reached', count=1)
