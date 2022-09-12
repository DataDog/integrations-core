# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import simplejson as json
from six import PY2
from six.moves.urllib.parse import urlparse

from datadog_checks.base import AgentCheck, ConfigurationError


class Kong(AgentCheck):
    """
    This is a legacy implementation that will be removed at some point, refer to check.py for the new implementation.
    """

    METRIC_PREFIX = 'kong.'

    HTTP_CONFIG_REMAPPER = {'ssl_validation': {'name': 'tls_verify'}}

    """ collects metrics for Kong """

    def __new__(cls, name, init_config, instances):
        instance = instances[0]

        if 'openmetrics_endpoint' in instance:
            if PY2:
                raise ConfigurationError(
                    "This version of the integration is only available when using py3. "
                    "Check https://docs.datadoghq.com/agent/guide/agent-v6-python-3 "
                    "for more information or use the older style config."
                )
            # TODO: when we drop Python 2 move this import up top
            from .check import KongCheck

            return KongCheck(name, init_config, instances)
        else:
            return super(Kong, cls).__new__(cls)

    def check(self, _):
        metrics = self._fetch_data()
        for row in metrics:
            try:
                name, value, tags = row
                self.gauge(name, value, tags)
            except Exception:
                self.log.error(u'Could not submit metric: %s', row)

    def _fetch_data(self):
        if 'kong_status_url' not in self.instance:
            raise Exception('missing "kong_status_url" value')
        tags = self.instance.get('tags', [])
        url = self.instance.get('kong_status_url')

        parsed_url = urlparse(url)
        host = parsed_url.hostname
        port = parsed_url.port or 80
        service_check_name = 'kong.can_connect'
        service_check_tags = ['kong_host:%s' % host, 'kong_port:%s' % port] + tags

        try:
            self.log.debug("Querying URL: %s", url)
            response = self.http.get(url)
            self.log.debug("Kong status `response`: %s", response)
            response.raise_for_status()
        except Exception:
            self.service_check(service_check_name, Kong.CRITICAL, tags=service_check_tags)
            raise
        else:
            if response.status_code == 200:
                self.service_check(service_check_name, Kong.OK, tags=service_check_tags)
            else:
                self.service_check(service_check_name, Kong.CRITICAL, tags=service_check_tags)

        return self._parse_json(response.content, tags)

    def _parse_json(self, raw, tags=None):
        if tags is None:
            tags = []
        parsed = json.loads(raw)
        output = []

        # Get the server stats
        for name, value in parsed.get('server').items():
            metric_name = self.METRIC_PREFIX + name
            output.append((metric_name, value, tags))

        return output
