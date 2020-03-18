# (C) Datadog, Inc. 2015-present
# (C) Takumi Sakamoto <takumi.saka@gmail.com> 2014
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import re

# 3rd party
from six.moves.urllib.parse import urlparse

# project
from datadog_checks.base.utils.subprocess_output import get_subprocess_output
from datadog_checks.base.checks import AgentCheck


class Fluentd(AgentCheck):
    DEFAULT_TIMEOUT = 5
    SERVICE_CHECK_NAME = 'fluentd.is_ok'
    GAUGES = ['retry_count', 'buffer_total_queued_size', 'buffer_queue_length']
    _AVAILABLE_TAGS = frozenset(['plugin_id', 'type'])
    VERSION_PATTERN = r'.* (?P<version>[0-9\.]+)'

    def __init__(self, name, init_config, instances):
        super(Fluentd, self).__init__(name, init_config, instances)
        if not ('read_timeout' in self.instance or 'connect_timeout' in self.instance):
            # `default_timeout` config option will be removed with Agent 5
            timeout = (
                self.instance.get('timeout')
                or self.instance.get('default_timeout')
                or self.init_config.get('timeout')
                or self.init_config.get('default_timeout')
                or self.DEFAULT_TIMEOUT
            )
            self.http.options['timeout'] = (timeout, timeout)

        self._fluentd_command = self.instance.get('fluentd', init_config.get('fluentd', 'fluentd'))

        self.url = self.instance.get('monitor_agent_url')
        parsed_url = urlparse(self.url)
        self.monitor_agent_host = parsed_url.hostname
        self.monitor_agent_port = parsed_url.port or 24220
        self.config_url = '{}://{}:{}/api/config.json'.format(
            parsed_url.scheme, self.monitor_agent_host, self.monitor_agent_port
        )

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

            plugin_ids = instance.get('plugin_ids', [])
            custom_tags = instance.get('tags', [])

            # Fallback  with `tag_by: plugin_id`
            tag_by = instance.get('tag_by')
            tag_by = tag_by if tag_by in self._AVAILABLE_TAGS else 'plugin_id'

            service_check_tags = [
                'fluentd_host:%s' % self.monitor_agent_host,
                'fluentd_port:%s' % self.monitor_agent_port,
            ] + custom_tags

            r = self.http.get(self.url)
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

            self._collect_metadata()
        except Exception as e:
            msg = "No stats could be retrieved from %s : %s" % (self.url, str(e))
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=service_check_tags, message=msg)
            raise
        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=service_check_tags)

    def _collect_metadata(self):
        raw_version = None
        if not self.is_metadata_collection_enabled():
            return

        try:
            r = self.http.get(self.config_url)
            r.raise_for_status()
            config = r.json()
            raw_version = config.get('version')
        except Exception as e:
            self.log.debug("No config could be retrieved from %s: %s", self.config_url, e)

        # Fall back to command line for older versions of fluentd
        if not raw_version:
            raw_version = self._get_version_from_command_line()
        if raw_version:
            self.set_metadata('version', raw_version)

    def _get_version_from_command_line(self):
        version_command = '{} --version'.format(self._fluentd_command)

        try:
            out, _, _ = get_subprocess_output(version_command, self.log, raise_on_empty_output=False)
        except OSError as exc:
            self.log.warning("Error collecting fluentd version: %s", exc)
            return None

        match = re.match(self.VERSION_PATTERN, out)

        if match is None:
            self.log.warning("fluentd version not found in stdout: `%s`", out)
            return None

        return match.group('version')
