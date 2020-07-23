# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re
from datetime import datetime
from itertools import chain

import simplejson as json
from six import PY3, iteritems, text_type
from six.moves.urllib.parse import urlparse

from datadog_checks.base import AgentCheck, ConfigurationError

from .metrics import METRICS_SEND_AS_COUNT, VTS_METRIC_MAP

if PY3:
    long = int

EPOCH = datetime(1970, 1, 1)

if hasattr(datetime, 'fromisoformat'):
    fromisoformat = datetime.fromisoformat
else:

    def fromisoformat(ts):
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")


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
    'slots': 'slot',
}


class Nginx(AgentCheck):
    """Tracks basic nginx metrics via the status module
    * number of connections
    * number of requests per second

    Requires nginx to have the status option compiled.
    See http://wiki.nginx.org/HttpStubStatusModule for more details

    $ curl http://localhost:81/nginx_status/
    Active connections: 8
    server accepts handled requests
     1156958 1156958 4491319
    Reading: 0 Writing: 2 Waiting: 6

    """

    HTTP_CONFIG_REMAPPER = {'ssl_validation': {'name': 'tls_verify'}, 'user': {'name': 'username'}}

    def check(self, instance):
        if 'nginx_status_url' not in instance:
            raise ConfigurationError('NginX instance missing "nginx_status_url" value.')

        tags = instance.get('tags', [])

        url, use_plus_api, plus_api_version = self._get_instance_params(instance)

        if not use_plus_api:
            response, content_type, version = self._get_data(instance, url)
            # for unpaid versions
            self._set_version_metadata(version)

            self.log.debug("Nginx status `response`: %s", response)
            self.log.debug("Nginx status `content_type`: %s", content_type)

            if content_type.startswith('application/json'):
                metrics = self.parse_json(response, tags)
            else:
                metrics = self.parse_text(response, tags)
        else:
            metrics = []
            self._perform_service_check(instance, '{}/{}'.format(url, plus_api_version))

            # These are all the endpoints we have to call to get the same data as we did with the old API
            # since we can't get everything in one place anymore.
            for endpoint, nest in chain(iteritems(PLUS_API_ENDPOINTS), iteritems(PLUS_API_STREAM_ENDPOINTS)):
                response = self._get_plus_api_data(url, plus_api_version, endpoint, nest)
                self.log.debug("Nginx Plus API version %s `response`: %s", plus_api_version, response)
                metrics.extend(self.parse_json(response, tags))

        funcs = {'gauge': self.gauge, 'rate': self.rate, 'count': self.monotonic_count}
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

                # for vts and plus versions
                if name == 'nginx.version':
                    self._set_version_metadata(value)

            except Exception as e:
                self.log.error('Could not submit metric: %s: %s', repr(row), e)

    @classmethod
    def _get_instance_params(cls, instance):
        url = instance.get('nginx_status_url')

        use_plus_api = instance.get("use_plus_api", False)
        plus_api_version = str(instance.get("plus_api_version", 2))

        return url, use_plus_api, plus_api_version

    def _get_data(self, instance, url):
        r = self._perform_service_check(instance, url)

        body = r.content
        resp_headers = r.headers
        return body, resp_headers.get('content-type', 'text/plain'), resp_headers.get('server')

    def _perform_request(self, url):
        r = self.http.get(url)
        r.raise_for_status()
        return r

    def _perform_service_check(self, instance, url):
        # Submit a service check for status page availability.
        parsed_url = urlparse(url)
        nginx_host = parsed_url.hostname
        nginx_port = parsed_url.port or 80
        custom_tags = instance.get('tags', [])
        if custom_tags is None:
            custom_tags = []

        service_check_name = 'nginx.can_connect'
        service_check_tags = ['host:%s' % nginx_host, 'port:%s' % nginx_port] + custom_tags
        try:
            self.log.debug("Querying URL: %s", url)
            r = self._perform_request(url)
        except Exception:
            self.service_check(service_check_name, AgentCheck.CRITICAL, tags=service_check_tags)
            raise
        else:
            self.service_check(service_check_name, AgentCheck.OK, tags=service_check_tags)
        return r

    def _nest_payload(self, keys, payload):
        """
        Nest a payload in a dict under the keys contained in `keys`
        """
        if len(keys) == 0:
            return payload

        return {keys[0]: self._nest_payload(keys[1:], payload)}

    def _get_plus_api_data(self, api_url, plus_api_version, endpoint, nest):
        # Get the data from the Plus API and reconstruct a payload similar to what the old API returned
        # so we can treat it the same way

        url = "/".join([api_url, plus_api_version, endpoint])
        payload = {}
        try:
            self.log.debug("Querying URL: %s", url)
            r = self._perform_request(url)
            payload = self._nest_payload(nest, r.json())
        except Exception as e:
            if endpoint in PLUS_API_STREAM_ENDPOINTS:
                self.log.warning(
                    "Stream may not be initialized. " "Error querying %s metrics at %s: %s", endpoint, url, e
                )
            else:
                self.log.exception("Error querying %s metrics at %s: %s", endpoint, url, e)

        return payload

    def _set_version_metadata(self, version):
        if version and version != 'nginx':
            if '/' in version:
                version = version.split('/')[1]
            self.set_metadata('version', version)

            self.log.debug("Nginx version `server`: %s", version)
        else:
            self.log.warning(u"could not retrieve nginx version info")

    @classmethod
    def parse_text(cls, raw, tags=None):
        # Thanks to http://hostingfu.com/files/nginx/nginxstats.py for this code
        # Connections
        if tags is None:
            tags = []
        output = []
        parsed = re.search(br'Active connections:\s+(\d+)', raw)
        if parsed:
            connections = int(parsed.group(1))
            output.append(('nginx.net.connections', connections, tags, 'gauge'))

        # Requests per second
        parsed = re.search(br'\s*(\d+)\s+(\d+)\s+(\d+)', raw)
        if parsed:
            conn = int(parsed.group(1))
            handled = int(parsed.group(2))
            request = int(parsed.group(3))
            output.extend(
                [
                    ('nginx.net.conn_opened_per_s', conn, tags, 'rate'),
                    ('nginx.net.conn_dropped_per_s', conn - handled, tags, 'rate'),
                    ('nginx.net.request_per_s', request, tags, 'rate'),
                ]
            )

        # Connection states, reading, writing or waiting for clients
        parsed = re.search(br'Reading: (\d+)\s+Writing: (\d+)\s+Waiting: (\d+)', raw)
        if parsed:
            reading, writing, waiting = parsed.groups()
            output.extend(
                [
                    ("nginx.net.reading", int(reading), tags, 'gauge'),
                    ("nginx.net.writing", int(writing), tags, 'gauge'),
                    ("nginx.net.waiting", int(waiting), tags, 'gauge'),
                ]
            )
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
            for key, val2 in iteritems(val):
                if key in TAGGED_KEYS:
                    metric_name = '%s.%s' % (metric_base, TAGGED_KEYS[key])
                    for tag_val, data in iteritems(val2):
                        tag = '%s:%s' % (TAGGED_KEYS[key], tag_val)
                        output.extend(cls._flatten_json(metric_name, data, tags + [tag]))
                else:
                    metric_name = '%s.%s' % (metric_base, key)
                    output.extend(cls._flatten_json(metric_name, val2, tags))

        elif isinstance(val, list):
            for val2 in val:
                output.extend(cls._flatten_json(metric_base, val2, tags))

        elif isinstance(val, bool):
            output.append((metric_base, int(val), tags, 'gauge'))

        elif isinstance(val, (int, float, long)):
            output.append((metric_base, val, tags, 'gauge'))

        elif isinstance(val, (text_type, str)):
            if val[-1] == "Z":
                try:
                    # In the new Plus API, timestamps are now formatted
                    # strings, some include microseconds, some don't...
                    timestamp = fromisoformat(val[:19])
                except ValueError:
                    pass
                else:
                    output.append((metric_base, int((timestamp - EPOCH).total_seconds()), tags, 'gauge'))

        return output
