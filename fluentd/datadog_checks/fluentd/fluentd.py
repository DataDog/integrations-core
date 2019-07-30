# (C) Datadog, Inc. 2015-2017
# (C) Takumi Sakamoto <takumi.saka@gmail.com> 2014
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# 3rd party
from six.moves.urllib.parse import urlparse

# project
from datadog_checks.checks import AgentCheck


class Fluentd(AgentCheck):
    DEFAULT_TIMEOUT = 5
    SERVICE_CHECK_NAME = 'fluentd.is_ok'
    GAUGES = ['retry_count', 'buffer_total_queued_size', 'buffer_queue_length']
    _AVAILABLE_TAGS = frozenset(['plugin_id', 'type'])

    def __init__(self, name, init_config, instances):
        super(Fluentd, self).__init__(name, init_config, instances)
        self.default_timeout = init_config.get('default_timeout', self.DEFAULT_TIMEOUT)

    """Tracks basic fluentd metrics via the monitor_agent plugin
    * number of retry_count
    * number of buffer_queue_length
    * number of buffer_total_queued_size

    $ curl http://localhost:24220/api/plugins.json
    {"plugins":[{"type": "monitor_agent", ...}, {"type": "forward", ...}]}
    """

    def check(self, instance):
        if 'monitor_agent_url' not in instance:
            raise Exception('Fluentd instance missing "monitor_agent_url" value.')

        try:
            url = instance.get('monitor_agent_url')
            plugin_ids = instance.get('plugin_ids', [])
            custom_tags = instance.get('tags', [])

            # Fallback  with `tag_by: plugin_id`
            tag_by = instance.get('tag_by')
            tag_by = tag_by if tag_by in self._AVAILABLE_TAGS else 'plugin_id'

            parsed_url = urlparse(url)
            monitor_agent_host = parsed_url.hostname
            monitor_agent_port = parsed_url.port or 24220
            service_check_tags = [
                'fluentd_host:%s' % monitor_agent_host,
                'fluentd_port:%s' % monitor_agent_port,
            ] + custom_tags

            r = self.http.get(url)
            r.raise_for_status()
            status = r.json()

            for p in status['plugins']:
                tag = "%s:%s" % (tag_by, p.get(tag_by))
                for m in self.GAUGES:
                    metric = p.get(m)
                    if metric is None:
                        continue
                    if m == 'retry_count':
                        # Since v1, retry_count counts the total number of errors.
                        # Use retry/steps field for temporal retry count instead.
                        rs = p.get("retry")
                        if rs is not None:
                            if rs.get("steps") is not None:
                                metric = rs.get("steps")
                            else:
                                metric = 0
                    # Filter unspecified plugins to keep backward compatibility.
                    if len(plugin_ids) == 0 or p.get('plugin_id') in plugin_ids:
                        self.gauge('fluentd.%s' % (m), metric, [tag] + custom_tags)
        except Exception as e:
            msg = "No stats could be retrieved from %s : %s" % (url, str(e))
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=service_check_tags, message=msg)
            raise
        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=service_check_tags)
