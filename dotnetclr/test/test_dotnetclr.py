# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from nose.plugins.attrib import attr

# 3p

# project
from tests.checks.common import AgentCheckTest

MINIMAL_INSTANCE = {
    'host': '.',
}

INSTANCE_WITH_TAGS = {
    'host': '.',
    'tags': ['tag1', 'another:tag']
}


@attr('windows')
@attr(requires='dotnetclr')
class DotNetCLRTest(AgentCheckTest):
    CHECK_NAME = 'dotnetclr'

    CLR_METRICS = (
        "dotnetclr.exceptions.thrown_persec",
        "dotnetclr.memory.time_in_gc",
        "dotnetclr.memory.committed.heap_bytes",
        "dotnetclr.memory.reserved.heap_bytes",
    )

    EXPECTED_INSTANCES = (
        "_Global_",
        "sqlservr",
        "Appveyor.BuildAgent.Interactive"
    )

    def test_basic_check(self):
        self.run_check_twice({'instances': [MINIMAL_INSTANCE]})

        for metric in self.CLR_METRICS:
            for inst in self.EXPECTED_INSTANCES:
                self.assertMetric(metric, tags=["instance:{0}".format(inst)], count=1)

        self.coverage_report()

    def test_with_tags(self):
        self.run_check_twice({'instances': [INSTANCE_WITH_TAGS]})

        for metric in self.CLR_METRICS:
            for inst in self.EXPECTED_INSTANCES:
                self.assertMetric(metric, tags=['tag1', 'another:tag', "instance:{0}".format(inst)], count=1)

        self.coverage_report()
