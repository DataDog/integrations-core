# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import psutil
from six import iteritems

from datadog_checks.base import AgentCheck


class SystemCore(AgentCheck):
    def check(self, instance):
        instance_tags = instance.get('tags', [])

        # https://psutil.readthedocs.io/en/latest/#psutil.cpu_count
        n_cpus = psutil.cpu_count()
        self.gauge('system.core.count', n_cpus, tags=instance_tags)

        # https://psutil.readthedocs.io/en/latest/#psutil.cpu_times
        cpu_times = psutil.cpu_times(percpu=True)

        for i, cpu in enumerate(cpu_times):
            tags = instance_tags + ['core:{0}'.format(i)]
            for key, value in iteritems(cpu._asdict()):
                self.rate('system.core.{0}'.format(key), value, tags=tags)

        cpu_times_total = psutil.cpu_times()
        for key, value in iteritems(cpu_times_total._asdict()):
            self.rate('system.core.{0}.total'.format(key), value, tags=instance_tags)

