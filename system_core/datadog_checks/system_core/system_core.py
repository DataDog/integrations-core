# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import psutil
from six import iteritems

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.platform import Platform


class SystemCore(AgentCheck):
    def check(self, instance):
        instance_tags = instance.get('tags', [])

        # https://psutil.readthedocs.io/en/latest/#psutil.cpu_times
        cpu_times = psutil.cpu_times(percpu=True)
        self.gauge('system.core.count', len(cpu_times), tags=instance_tags)
        self.log.debug('CPU times: %s', str(cpu_times))

        for i, cpu in enumerate(cpu_times):
            tags = instance_tags + ['core:{0}'.format(i)]
            for key, value in iteritems(cpu._asdict()):
                self.rate('system.core.{0}'.format(key), 100.0 * value, tags=tags)

        total_cpu_times = psutil.cpu_times()
        for key, value in iteritems(total_cpu_times._asdict()):
            self.rate('system.core.{0}.total'.format(key), 100.0 * value / len(cpu_times), tags=instance_tags)

        # https://psutil.readthedocs.io/en/latest/#psutil.cpu_freq
        # scpufreq(current=2236.812, min=800.0, max=3500.0)
        # Ignore min/max as they are often reported as 0.0 if undetermined.
        cpu_freq = psutil.cpu_freq(percpu=True)
        self.log.debug('CPU frequency: %s', str(cpu_freq))
        for i, cpu in enumerate(cpu_freq):
            if Platform.is_unix():
                # Per-cpu frequency retrieval (Linux only)
                tags = instance_tags + ['core:{0}'.format(i)]
            self.gauge('system.core.frequency', cpu._asdict().get('current'), tags=tags)
