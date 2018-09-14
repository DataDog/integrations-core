# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re
import urlparse
import time
from itertools import chain

from datetime import datetime

import requests
import simplejson as json

from datadog_checks.checks import AgentCheck
from datadog_checks.utils.headers import headers
from datadog_checks.nginx.metrics import VTS_METRIC_MAP, METRICS_SEND_AS_COUNT

PLUS_API_ENDPOINTS = {
    "nginx": [],
    "http/requests": ["requests"],
    "http/server_zones": ["server_zones"],
    "http/upstreams": ["upstreams"],
    "http/caches": ["caches"],
    "processes": ["processes"],
    "connections": ["connections"],
    "ssl": ["ssl"],
    "slabs": ["slabs"],
}

PLUS_API_STREAM_ENDPOINTS = {
    "stream/server_zones": ["stream", "server_zones"],
    "stream/upstreams": ["stream", "upstreams"],
}

TAGGED_KEYS = {
    'caches': 'cache',
    'server_zones': 'server_zone',
    'serverZones': 'server_zone',  # VTS
    'upstreams': 'upstream',
    'upstreamZones': 'upstream',  # VTS
    'slabs': 'slab',
    'slots': 'slot'
}


class Nginx(AgentCheck):
    """Tracks basic nginx metrics via the status module
    * number of connections
    * number of requets per second

    Requires nginx to have the status option compiled.
    See http://wiki.nginx.org/HttpStubStatusModule for more details

    $ curl http://localhost:81/nginx_status/
    Active connections: 8
    server accepts handled requests
     1156958 1156958 4491319
    Reading: 0 Writing: 2 Waiting: 6

    """
    def check(self, instance):

        if 'nginx_status_url' not in instance:
            raise Exception('NginX instance missing "nginx_status_url" value.')
        tags = instance.get('tags', [])

        url, ssl_validation, auth, use_plus_api, plus_api_version = self._get_instance_params(instance)

        if not use_plus_api:
            response, content_type = self._get_data(instance, url, ssl_validation, auth)
            self.log.debug(u"Nginx status `response`: {0}".format(response))
            self.log.debug(u"Nginx status `content_type`: {0}".format(content_type))

            if content_type.startswith('application/json'):
                metrics = self.parse_json(response, tags)
            else:
                metrics = self.parse_text(response, tags)
        else:
            metrics = []
            self._perform_service_check(instance, "/".join([url, plus_api_version]), ssl_validation, auth)
            # These are all the endpoints we have to call to get the same data as we did with the old API
            # since we can't get everything in one place anymore.

            for endpoint, nest in chain(PLUS_API_ENDPOINTS.iteritems(), PLUS_API_STREAM_ENDPOINTS.iteritems()):
                response = self._get_plus_api_data(instance, url, ssl_validation, auth,
                                                   plus_api_version, endpoint, nest)
                self.log.debug(u"Nginx Plus API version {0} `response`: {1}".format(plus_api_version, response))
                metrics.extend(self.parse_json(response, tags))

        funcs = {
            'gauge': self.gauge,
            'rate': self.rate,
            'count': self.monotonic_count
        }
        conn = None
        handled = None
        for row in metrics:
            try:
                name, value, tags, metric_type = row

                # Translate metrics received from VTS
                if instance.get('use_vts', False):
                    # Requests per second
                    if name == 'nginx.connections.handled':
                        handled = value
                    if name == 'nginx.connections.accepted':
                        conn = value
                        self.rate('nginx.net.conn_opened_per_s', conn, tags)
                    if handled is not None and conn is not None:
                        self.rate('nginx.net.conn_dropped_per_s', conn - handled, tags)
                        handled = None
                        conn = None
                    if name == 'nginx.connections.requests':
                        self.rate('nginx.net.request_per_s', value, tags)

                    name = VTS_METRIC_MAP.get(name)
                    if name is None:
                        continue

                if name in METRICS_SEND_AS_COUNT:
                    func_count = funcs['count']
                    func_count(name + "_count", value, tags)
                func = funcs[metric_type]
                func(name, value, tags)
            except Exception as e:
                self.log.error(u'Could not submit metric: %s: %s' % (repr(row), str(e)))

    def _get_instance_params(self, instance):
        url = instance.get('nginx_status_url')
        ssl_validation = instance.get('ssl_validation', True)

        auth = None
        if 'user' in instance and 'password' in instance:
            auth = (instance['user'], instance['password'])

        use_plus_api = instance.get("use_plus_api", False)
        plus_api_version = str(instance.get("plus_api_version", 2))

        return url, ssl_validation, auth, use_plus_api, plus_api_version

    def _get_data(self, instance, url, ssl_validation, auth):

        r = self._perform_service_check(instance, url, ssl_validation, auth)

        body = r.content
        resp_headers = r.headers
        return body, resp_headers.get('content-type', 'text/plain')

    def _perform_request(self, instance, url, ssl_validation, auth):
        r = requests.get(url, auth=auth, headers=headers(self.agentConfig),
                         verify=ssl_validation, timeout=self.default_integration_http_timeout,
                         proxies=self.get_instance_proxy(instance, url))
        r.raise_for_status()
        return r

    def _perform_service_check(self, instance, url, ssl_validation, auth):
        # Submit a service check for status page availability.
        parsed_url = urlparse.urlparse(url)
        nginx_host = parsed_url.hostname
        nginx_port = parsed_url.port or 80
        custom_tags = instance.get('tags', [])
        if custom_tags is None:
            custom_tags = []

        service_check_name = 'nginx.can_connect'
        service_check_tags = ['host:%s' % nginx_host, 'port:%s' % nginx_port] + custom_tags
        try:
            self.log.debug(u"Querying URL: {0}".format(url))
            r = self._perform_request(instance, url, ssl_validation, auth)
        except Exception:
            self.service_check(service_check_name, AgentCheck.CRITICAL,
                               tags=service_check_tags)
            raise
        else:
            self.service_check(service_check_name, AgentCheck.OK,
                               tags=service_check_tags)
        return r

    def _nest_payload(self, keys, payload):
        """
        Nest a payload in a dict under the keys contained in `keys`
        """
        if len(keys) == 0:
            return payload

        return {
            keys[0]: self._nest_payload(keys[1:], payload)
        }

    def _get_plus_api_data(self, instance, api_url, ssl_validation, auth, plus_api_version, endpoint, nest):
        # Get the data from the Plus API and reconstruct a payload similar to what the old API returned
        # so we can treat it the same way

        url = "/".join([api_url, plus_api_version, endpoint])
        payload = {}
        try:
            self.log.debug(u"Querying URL: {0}".format(url))
            r = self._perform_request(instance, url, ssl_validation, auth)
            payload = self._nest_payload(nest, r.json())
        except Exception as e:
            if endpoint in PLUS_API_STREAM_ENDPOINTS:
                self.log.warning("Stream may not be initialized. "
                                 "Error querying {} metrics at {}: {}".format(endpoint, url, e))
            else:
                self.log.exception("Error querying {} metrics at {}: {}".format(endpoint, url, e))

        return payload

    @classmethod
    def parse_text(cls, raw, tags=None):
        # Thanks to http://hostingfu.com/files/nginx/nginxstats.py for this code
        # Connections
        if tags is None:
            tags = []
        output = []
        parsed = re.search(r'Active connections:\s+(\d+)', raw)
        if parsed:
            connections = int(parsed.group(1))
            output.append(('nginx.net.connections', connections, tags, 'gauge'))

        # Requests per second
        parsed = re.search(r'\s*(\d+)\s+(\d+)\s+(\d+)', raw)
        if parsed:
            conn = int(parsed.group(1))
            handled = int(parsed.group(2))
            requests = int(parsed.group(3))
            output.extend([('nginx.net.conn_opened_per_s', conn, tags, 'rate'),
                           ('nginx.net.conn_dropped_per_s', conn - handled, tags, 'rate'),
                           ('nginx.net.request_per_s', requests, tags, 'rate')])

        # Connection states, reading, writing or waiting for clients
        parsed = re.search(r'Reading: (\d+)\s+Writing: (\d+)\s+Waiting: (\d+)', raw)
        if parsed:
            reading, writing, waiting = parsed.groups()
            output.extend([
                ("nginx.net.reading", int(reading), tags, 'gauge'),
                ("nginx.net.writing", int(writing), tags, 'gauge'),
                ("nginx.net.waiting", int(waiting), tags, 'gauge'),
            ])
        return output

    @classmethod
    def parse_json(cls, raw, tags=None):
        if tags is None:
            tags = []
        if isinstance(raw, dict):
            parsed = raw
        else:
            parsed = json.loads(raw)
        metric_base = 'nginx'

        return cls._flatten_json(metric_base, parsed, tags)

    @classmethod
    def _flatten_json(cls, metric_base, val, tags):
        """
        Recursively flattens the nginx json object. Returns the following: [(metric_name, value, tags)]
        """
        output = []

        if isinstance(val, dict):
            # Pull out the server as a tag instead of trying to read as a metric
            if 'server' in val and val['server']:
                server = 'server:%s' % val.pop('server')
                if tags is None:
                    tags = [server]
                else:
                    tags = tags + [server]
            for key, val2 in val.iteritems():
                if key in TAGGED_KEYS:
                    metric_name = '%s.%s' % (metric_base, TAGGED_KEYS[key])
                    for tag_val, data in val2.iteritems():
                        tag = '%s:%s' % (TAGGED_KEYS[key], tag_val)
                        output.extend(cls._flatten_json(metric_name, data, tags + [tag]))
                else:
                    metric_name = '%s.%s' % (metric_base, key)
                    output.extend(cls._flatten_json(metric_name, val2, tags))

        elif isinstance(val, list):
            for val2 in val:
                output.extend(cls._flatten_json(metric_base, val2, tags))

        elif isinstance(val, bool):
            # Turn bools into 0/1 values
            if val:
                val = 1
            else:
                val = 0
            output.append((metric_base, val, tags, 'gauge'))

        elif isinstance(val, (int, float, long)):
            output.append((metric_base, val, tags, 'gauge'))

        elif isinstance(val, (unicode, str)):
            # In the new Plus API, timestamps are now formatted strings, some include microseconds, some don't...
            try:
                timestamp = time.mktime(datetime.strptime(val, "%Y-%m-%dT%H:%M:%S.%fZ").timetuple())
                output.append((metric_base, timestamp, tags, 'gauge'))
            except ValueError:
                try:
                    timestamp = time.mktime(datetime.strptime(val, "%Y-%m-%dT%H:%M:%SZ").timetuple())
                    output.append((metric_base, timestamp, tags, 'gauge'))
                except ValueError:
                    pass

        return output
