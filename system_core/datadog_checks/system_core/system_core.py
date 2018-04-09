# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import psutil

from datadog_checks.checks import AgentCheck


class SystemCore(AgentCheck):
    def check(self, instance):
        instance_tags = instance.get('tags', [])

        cpu_times = psutil.cpu_times(percpu=True)
        self.gauge('system.core.count', len(cpu_times), tags=instance_tags)

        for i, cpu in enumerate(cpu_times):
            tags = instance_tags + ['core:{0}'.format(i)]
            for key, value in cpu._asdict().iteritems():
                self.rate(
                    'system.core.{0}'.format(key),
                    100.0 * value,
                    tags=tags
                )
