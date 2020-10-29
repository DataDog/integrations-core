# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import json
import random
import time

from flup.client.fcgi_app import FCGIApp
from six import PY3, StringIO, iteritems, string_types
from six.moves.urllib.parse import urlparse

from datadog_checks.base import AgentCheck, is_affirmative

# Relax param filtering
FCGIApp._environPrefixes.extend(('DOCUMENT_', 'SCRIPT_'))

# Flup as of 1.0.3 is not fully compatible with Python 3 yet.
# This fixes that for our use case.
# https://hg.saddi.com/flup-py3.0/file/tip/flup/client/fcgi_app.py
if PY3:
    import socket

    def get_connection(self):
        if self._connect is not None:
            if isinstance(self._connect, string_types):
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(self._connect)
            elif hasattr(socket, 'create_connection'):
                sock = socket.create_connection(self._connect)
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(self._connect)
            return sock

    FCGIApp._getConnection = get_connection


DEFAULT_TIMEOUT = 20


class BadConfigError(Exception):
    pass


class PHPFPMCheck(AgentCheck):
    """
    Tracks basic php-fpm metrics via the status module
    Requires php-fpm pools to have the status option.
    See http://www.php.net/manual/de/install.fpm.configuration.php#pm.status-path for more details
    """

    SERVICE_CHECK_NAME = 'php_fpm.can_ping'

    GAUGES = {
        'listen queue': 'php_fpm.listen_queue.size',
        'idle processes': 'php_fpm.processes.idle',
        'active processes': 'php_fpm.processes.active',
        'total processes': 'php_fpm.processes.total',
    }

    MONOTONIC_COUNTS = {
        'accepted conn': 'php_fpm.requests.accepted',
        'max children reached': 'php_fpm.processes.max_reached',
        'slow requests': 'php_fpm.requests.slow',
    }

    HTTP_CONFIG_REMAPPER = {
        'user': {'name': 'username'},
        'disable_ssl_validation': {'name': 'tls_verify', 'invert': True, 'default': False},
    }

    def __init__(self, name, init_config, instances):
        super(PHPFPMCheck, self).__init__(name, init_config, instances)
        if 'http_host' in self.instance:
            self.http.options['headers']['Host'] = self.instance['http_host']

    def check(self, _):
        status_url = self.instance.get('status_url')
        ping_url = self.instance.get('ping_url')
        use_fastcgi = is_affirmative(self.instance.get('use_fastcgi', False))
        ping_reply = self.instance.get('ping_reply')

        tags = self.instance.get('tags', [])
        http_host = self.instance.get('http_host')

        if status_url is None and ping_url is None:
            raise BadConfigError("No status_url or ping_url specified for this instance")

        pool = None
        if status_url is not None:
            try:
                pool = self._process_status(status_url, tags, http_host, use_fastcgi)
            except Exception as e:
                self.log.error("Error running php_fpm check: %s", e)

        if ping_url is not None:
            self._process_ping(ping_url, ping_reply, tags, pool, http_host, use_fastcgi)

    def _process_status(self, status_url, tags, http_host, use_fastcgi):
        data = {}
        try:
            if use_fastcgi:
                data = json.loads(self.request_fastcgi(status_url, query='json'))
            else:
                # TODO: adding the 'full' parameter gets you per-process detailed
                # informations, which could be nice to parse and output as metrics
                max_attempts = 3
                for i in range(max_attempts):
                    resp = self.http.get(status_url, params={'json': True})

                    # Exponential backoff, wait at most (max_attempts - 1) times in case we get a 503.
                    # Delay in seconds is (2^i + random amount of seconds between 0 and 1)
                    # 503s originated here: https://github.com/php/php-src/blob/d84ef96/sapi/fpm/fpm/fpm_status.c#L96
                    if resp.status_code == 503 and i < max_attempts - 1:
                        # retry
                        time.sleep(2 ** i + random.random())
                        continue

                    resp.raise_for_status()
                    data = resp.json()

                    # successfully got a response, exit the backoff system
                    break
        except Exception as e:
            self.log.error("Failed to get metrics from %s: %s", status_url, e)
            raise

        pool_name = data.get('pool', 'default')
        metric_tags = tags + ["pool:{0}".format(pool_name)]
        if http_host is not None:
            metric_tags += ["http_host:{0}".format(http_host)]

        for key, mname in iteritems(self.GAUGES):
            if key not in data:
                self.log.warning("Gauge metric %s is missing from FPM status", key)
                continue
            self.gauge(mname, int(data[key]), tags=metric_tags)

        for key, mname in iteritems(self.MONOTONIC_COUNTS):
            if key not in data:
                self.log.warning("Counter metric %s is missing from FPM status", key)
                continue
            self.monotonic_count(mname, int(data[key]), tags=metric_tags)

        # return pool, to tag the service check with it if we have one
        return pool_name

    def _process_ping(self, ping_url, ping_reply, tags, pool_name, http_host, use_fastcgi):
        if ping_reply is None:
            ping_reply = 'pong'

        sc_tags = ["ping_url:{0}".format(ping_url)] + tags
        if http_host is not None:
            sc_tags += ["http_host:{0}".format(http_host)]

        try:
            # TODO: adding the 'full' parameter gets you per-process detailed
            # information, which could be nice to parse and output as metrics
            if use_fastcgi:
                response = self.request_fastcgi(ping_url).decode('utf-8')
            else:
                resp = self.http.get(ping_url)
                resp.raise_for_status()
                response = resp.text

            if ping_reply not in response:
                raise Exception("Received unexpected reply to ping: {}".format(response))

        except Exception as e:
            self.log.error("Failed to ping FPM pool %s on URL %s: %s", pool_name, ping_url, e)
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=sc_tags, message=str(e))
        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=sc_tags)

    @classmethod
    def request_fastcgi(cls, url, query=''):
        parsed_url = urlparse(url)

        if parsed_url.scheme == "unix":
            # Example of expected format: unix:///path/to/file.sock/ping
            sock_file, _, route = parsed_url.path.partition('.sock')
            sock_file += '.sock'
            hostname = 'localhost'
            port = '80'
            fcgi = FCGIApp(connect=sock_file)
        else:
            hostname = parsed_url.hostname
            if hostname == 'localhost':
                hostname = '127.0.0.1'
            port = str(parsed_url.port or 9000)
            route = parsed_url.path
            fcgi = FCGIApp(host=hostname, port=port)

        env = {
            'CONTENT_LENGTH': '0',
            'CONTENT_TYPE': '',
            'DOCUMENT_ROOT': '/',
            'GATEWAY_INTERFACE': 'FastCGI/1.1',
            'QUERY_STRING': query,
            'REDIRECT_STATUS': '200',
            'REMOTE_ADDR': '127.0.0.1',
            'REMOTE_PORT': '80',
            'REQUEST_METHOD': 'GET',
            'REQUEST_URI': route,
            'SCRIPT_FILENAME': route,
            'SCRIPT_NAME': route,
            'SERVER_ADDR': hostname,
            'SERVER_NAME': hostname,
            'SERVER_PORT': port,
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'SERVER_SOFTWARE': 'datadog-php-fpm',
            'wsgi.errors': StringIO(),
            'wsgi.input': StringIO(),
        }

        # Return first response
        return fcgi(env, lambda *args, **kwargs: '')[0]
