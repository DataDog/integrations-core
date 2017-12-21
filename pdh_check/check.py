# (C) Datadog, Inc. 2013-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# project
from checks import AgentCheck
from utils.containers import hash_mutable
# datadog
try:
    from checks.libs.win.winpdh import WinPDHCounter
except ImportError:
    def WinPDHCounter(*args, **kwargs):
        return


class PDHCheck(AgentCheck):
    """
    WMI check.

    Windows only.
    """
    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self._countersettypes = {}
        self._counters = {}
        self._metrics = {}
        self._tags = {}

        try:
            for instance in instances:
                key = hash_mutable(instance)
                counterset = instance.get('countersetname')

                cfg_tags = instance.get('tags')
                if cfg_tags is not None:
                    tags = cfg_tags.join(",")
                    self._tags[key] = list(tags) if tags else []

                metrics = instance.get('metrics')
                # list of the metrics.  Each entry is itself an entry,
                # which is the pdh name, datadog metric name, type, and the
                # pdh counter object
                self._metrics[key] = []
                for inst_name, dd_name, mtype in metrics:
                    m = getattr(self, mtype.lower())
                    obj = WinPDHCounter(counterset, inst_name, self.log)
                    entry = [inst_name, dd_name, m, obj]
                    self.log.debug("entry: %s" % str(entry))
                    self._metrics[key].append(entry)

        except Exception as e:
            self.log.debug("Exception in PDH init: %s", str(e))
            raise

    def check(self, instance):
        key = hash_mutable(instance)
        for inst_name, dd_name, metric_func, counter in self._metrics[key]:
            vals = counter.get_all_values()
            for key, val in vals.iteritems():
                tags = []
                if key in self._tags:
                    tags = self._tags[key]

                if not counter.is_single_instance():
                    tag = "instance:%s" % key
                    tags.append(tag)
                metric_func(dd_name, val, tags)
