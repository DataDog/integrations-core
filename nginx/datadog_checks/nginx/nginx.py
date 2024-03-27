# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re
from datetime import datetime
from itertools import chain

import simplejson as json
from six import PY3, iteritems, text_type
from six.moves.urllib.parse import urljoin, urlparse

from datadog_checks.base import AgentCheck, ConfigurationError, to_native_string
from datadog_checks.base.utils.time import get_timestamp

from .const import PLUS_API_ENDPOINTS, PLUS_API_STREAM_ENDPOINTS, TAGGED_KEYS
from .metrics import COUNT_METRICS, METRICS_SEND_AS_COUNT, METRICS_SEND_AS_HISTOGRAM, VTS_METRIC_MAP

if PY3:
    long = int

if hasattr(datetime, 'fromisoformat'):
    fromisoformat = datetime.fromisoformat
else:

    def fromisoformat(ts):
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")


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

    def __init__(self, name, init_config, instances):
        super(Nginx, self).__init__(name, init_config, instances)
        self.custom_tags = self.instance.get('tags', [])
        self.url = self.instance.get('nginx_status_url')
        parsed_url = urlparse(self.url)
        self._nginx_hostname = parsed_url.hostname
        self._nginx_port = parsed_url.port or 80
        self.use_plus_api = self.instance.get("use_plus_api", False)
        self.use_plus_api_stream = self.instance.get("use_plus_api_stream", True)
        self.only_query_enabled_endpoints = self.instance.get("only_query_enabled_endpoints", False)
        self.plus_api_version = str(self.instance.get("plus_api_version", 2))
        self.use_vts = self.instance.get('use_vts', False)

        if 'nginx_status_url' not in self.instance:
            raise ConfigurationError('NginX instance missing "nginx_status_url" value.')

    def check(self, _):
        if not self.use_plus_api:
            metrics = self.collect_unit_metrics()
        else:
            metrics = self.collect_plus_metrics()

        metric_submission_funcs = {'gauge': self.gauge, 'rate': self.rate, 'count': self.monotonic_count}
        conn = None
        handled = None

        for row in metrics:
            try:
                name, value, row_tags, metric_type = row
                tags = row_tags + ['nginx_host:%s' % self._nginx_hostname, 'port:%s' % self._nginx_port]
                if self.use_vts:
                    name, handled, conn = self._translate_from_vts(name, value, tags, handled, conn)
                    if name is None:
                        continue

                if name in COUNT_METRICS:
                    self.monotonic_count(name, value, tags)
                else:
                    if name in METRICS_SEND_AS_COUNT:
                        self.monotonic_count(name + "_count", value, tags)
                    if name in METRICS_SEND_AS_HISTOGRAM:
                        self.histogram(name + "_histogram", value, tags)

                    func = metric_submission_funcs[metric_type]
                    func(name, value, tags)

            except Exception as e:
                self.log.error('Could not submit metric: %s: %s', repr(row), e)

    def _get_enabled_endpoints(self):
        """
        Dynamically determines which NGINX endpoints are enabled and Datadog supports getting metrics from
        by querying the NGINX APIs that list availabled endpoints. If an error is encountered,
        then it falls back to query all of the known endpoints available in the given NGINX Plus version.
        """
        available_endpoints = set()

        base_url = urljoin(self.url + "/", self.plus_api_version)
        http_url = urljoin(self.url + "/", self.plus_api_version + "/http")
        stream_url = urljoin(self.url + "/", self.plus_api_version + "/stream")

        try:
            self.log.debug("Querying base API url: %s", base_url)
            r = self._perform_request(base_url)
            r.raise_for_status()
            available_endpoints = set(r.json())
            http_avail = "http" in available_endpoints
            stream_avail = "stream" in available_endpoints

            if http_avail:
                self.log.debug("Querying http API url: %s", http_url)
                r = self._perform_request(http_url)
                r.raise_for_status()
                endpoints = set(r.json())
                http_endpoints = {'http/{}'.format(endpoint) for endpoint in endpoints}
                available_endpoints = available_endpoints.union(http_endpoints)

            if self.use_plus_api_stream and stream_avail:
                self.log.debug("Querying stream API url: %s", stream_url)
                r = self._perform_request(stream_url)
                r.raise_for_status()
                endpoints = set(r.json())
                stream_endpoints = {'stream/{}'.format(endpoint) for endpoint in endpoints}
                available_endpoints = available_endpoints.union(stream_endpoints)

            self.log.debug("Available endpoints are %s", available_endpoints)

            supported_endpoints = self._supported_endpoints(available_endpoints)
            self.log.debug("Supported endpoints are %s", supported_endpoints)
            return chain(iteritems(supported_endpoints))
        except Exception as e:
            self.log.warning(
                "Could not determine available endpoints from the API, "
                "falling back to monitor all endpoints supported in nginx version %s, %s",
                self.plus_api_version,
                str(e),
            )
            return self._get_all_plus_api_endpoints()

    def _supported_endpoints(self, available_endpoints):
        """
        Returns the endpoints that are both supported by this NGINX instance, and
        that the integration supports collecting metrics from
        """
        return {
            endpoint: nest for endpoint, nest in self._get_all_plus_api_endpoints() if endpoint in available_endpoints
        }

    def collect_plus_metrics(self):
        metrics = []
        self._perform_service_check('{}/{}'.format(self.url, self.plus_api_version))

        # These are all the endpoints we have to call to get the same data as we did with the old API
        # since we can't get everything in one place anymore.

        plus_api_chain_list = (
            self._get_enabled_endpoints() if self.only_query_enabled_endpoints else self._get_all_plus_api_endpoints()
        )

        for endpoint, nest in plus_api_chain_list:
            response = self._get_plus_api_data(endpoint, nest)

            if endpoint == 'nginx':
                try:
                    if isinstance(response, dict):
                        version_plus = response.get('version')
                    else:
                        version_plus = json.loads(response).get('version')
                    self._set_version_metadata(version_plus)
                except Exception as e:
                    self.log.debug("Couldn't submit nginx version: %s", e)

            self.log.debug("Nginx Plus API version %s `response`: %s", self.plus_api_version, response)
            metrics.extend(self.parse_json(response, self.custom_tags))
        return metrics

    def collect_unit_metrics(self):
        response, content_type, version = self._get_data()
        # for unpaid versions
        self._set_version_metadata(version)

        self.log.debug("Nginx status `response`: %s", response)
        self.log.debug("Nginx status `content_type`: %s", content_type)

        if content_type.startswith('application/json'):
            metrics = self.parse_json(response, self.custom_tags)
        else:
            metrics = self.parse_text(response, self.custom_tags)
        return metrics

    def _translate_from_vts(self, name, value, tags, handled, conn):
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
        return name, handled, conn

    def _get_data(self):
        r = self._perform_service_check(self.url)
        body = r.content
        resp_headers = r.headers
        return body, resp_headers.get('content-type', 'text/plain'), resp_headers.get('server')

    def _perform_request(self, url):
        r = self.http.get(url)
        r.raise_for_status()
        return r

    def _perform_service_check(self, url):
        # Submit a service check for status page availability.
        service_check_name = 'nginx.can_connect'
        service_check_tags = ['host:%s' % self._nginx_hostname, 'port:%s' % self._nginx_port] + self.custom_tags
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

    def _get_plus_api_endpoints(self, use_stream=False):
        """
        Returns all of either stream or default endpoints that the integration supports
        collecting metrics from based on the Plus API version
        """
        endpoints = iteritems({})

        available_plus_endpoints = PLUS_API_STREAM_ENDPOINTS if use_stream else PLUS_API_ENDPOINTS

        for earliest_version, new_endpoints in available_plus_endpoints.items():
            if int(self.plus_api_version) >= int(earliest_version):
                endpoints = chain(endpoints, iteritems(new_endpoints))
        return endpoints

    def _get_all_plus_api_endpoints(self):
        """
        Returns endpoints that the integration supports collecting metrics from based on the Plus API version
        """
        endpoints = self._get_plus_api_endpoints()

        if self.use_plus_api_stream:
            endpoints = chain(endpoints, self._get_plus_api_endpoints(use_stream=True))

        return endpoints

    def _get_plus_api_data(self, endpoint, nest):
        # Get the data from the Plus API and reconstruct a payload similar to what the old API returned
        # so we can treat it the same way

        url = "/".join([self.url, self.plus_api_version, endpoint])
        payload = {}
        try:
            self.log.debug("Querying URL: %s", url)
            r = self._perform_request(url)
            payload = self._nest_payload(nest, r.json())
        except Exception as e:
            plus_endpoints = self.list_endpoints(PLUS_API_STREAM_ENDPOINTS)
            if not self.only_query_enabled_endpoints and endpoint in plus_endpoints:
                self.log.warning(
                    "Error querying %s metrics at %s: %s. Stream may not be initialized, "
                    "you can avoid this error by enabling `only_query_enabled_endpoints` option.",
                    endpoint,
                    url,
                    e,
                )
            else:
                self.log.exception("Error querying %s metrics at %s: %s", endpoint, url, e)

        return payload

    @AgentCheck.metadata_entrypoint
    def _set_version_metadata(self, version):
        if version and version != 'nginx':
            if '/' in version:
                version = version.split('/')[1]
            self.set_metadata('version', version)

            self.log.debug("Nginx version `server`: %s", version)
        else:
            self.log.debug(u"could not retrieve nginx version info")

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
                    tags = []
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

        elif isinstance(val, (text_type, str)) and val[-1] == "Z":
            try:
                # In the new Plus API, timestamps are now formatted
                # strings, some include microseconds, some don't...
                timestamp = fromisoformat(val[:19])
            except ValueError:
                pass
            else:
                output.append((metric_base, int(get_timestamp(timestamp)), tags, 'gauge'))
        return output

    # override
    def _normalize_tags_type(self, tags, device_name=None, metric_name=None):
        if self.disable_generic_tags:
            return super(Nginx, self)._normalize_tags_type(tags, device_name, metric_name)
        # If disable_generic_tags is not enabled, for each generic tag we emmit both the generic and the non generic
        # version to ease transition.
        normalized_tags = []
        for tag in tags:
            if tag is not None:
                try:
                    tag = to_native_string(tag)
                except UnicodeError:
                    self.log.warning('Encoding error with tag `%s` for metric `%s`, ignoring tag', tag, metric_name)
                    continue
                normalized_tags.extend(list({tag, self.degeneralise_tag(tag)}))
        return normalized_tags

    def list_endpoints(self, api_dict_list):
        endpoints = [endpoint for api_dict in list(api_dict_list.values()) for endpoint in api_dict.keys()]
        return endpoints
