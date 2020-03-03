# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import simplejson as json
from six.moves.urllib.parse import urlparse

from datadog_checks.checks import AgentCheck


class Kong(AgentCheck):

    METRIC_PREFIX = 'kong.'

    HTTP_CONFIG_REMAPPER = {'ssl_validation': {'name': 'tls_verify'}}

    """ collects metrics for Kong """

    def check(self, instance):
        metrics = self._fetch_data(instance)
        for row in metrics:
            try:
                name, value, tags = row
                self.gauge(name, value, tags)
            except Exception:
                self.log.error(u'Could not submit metric: %s', row)

    def _fetch_data(self, instance):
        if 'kong_status_url' not in instance:
            raise Exception('missing "kong_status_url" value')
        tags = instance.get('tags', [])
        url = instance.get('kong_status_url')

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

        # First get the server stats
        for name, value in parsed.get('server').items():
            metric_name = self.METRIC_PREFIX + name
            output.append((metric_name, value, tags))

        # Then the database metrics
        databases_metrics = parsed.get('database').items()
        output.append((self.METRIC_PREFIX + 'table.count', len(databases_metrics), tags))
        for name, items in databases_metrics:
            output.append((self.METRIC_PREFIX + 'table.items', items, tags + ['table:{}'.format(name)]))

        return output
