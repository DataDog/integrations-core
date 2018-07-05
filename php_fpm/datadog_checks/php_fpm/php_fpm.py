# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import random
import time

import requests

from datadog_checks.checks import AgentCheck
from datadog_checks.utils.headers import headers
from datadog_checks.config import _is_affirmative

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

    def check(self, instance):
        status_url = instance.get('status_url')
        ping_url = instance.get('ping_url')
        ping_reply = instance.get('ping_reply')

        auth = None
        user = instance.get('user')
        password = instance.get('password')

        tags = instance.get('tags', [])
        http_host = instance.get('http_host')

        timeout = instance.get('timeout', DEFAULT_TIMEOUT)

        disable_ssl_validation = _is_affirmative(instance.get('disable_ssl_validation', False))

        if user and password:
            auth = (user, password)

        if status_url is None and ping_url is None:
            raise BadConfigError("No status_url or ping_url specified for this instance")

        pool = None
        if status_url is not None:
            try:
                pool = self._process_status(status_url, auth, tags, http_host, timeout, disable_ssl_validation)
            except Exception as e:
                self.log.error("Error running php_fpm check: {}".format(e))

        if ping_url is not None:
            self._process_ping(ping_url, ping_reply, auth, tags, pool, http_host, timeout, disable_ssl_validation)

    def _process_status(self, status_url, auth, tags, http_host, timeout, disable_ssl_validation):
        data = {}
        try:
            # TODO: adding the 'full' parameter gets you per-process detailed
            # informations, which could be nice to parse and output as metrics
            for i in range(3):
                resp = requests.get(status_url, auth=auth, timeout=timeout,
                                    headers=headers(self.agentConfig, http_host=http_host),
                                    verify=not disable_ssl_validation, params={'json': True})

                # Exponential backoff in case we get a 503 for at most 3 times.
                # Delay in seconds is (attempt + random amount of seconds between 0 and 1)
                # 503s originated here: https://github.com/php/php-src/blob/d84ef96/sapi/fpm/fpm/fpm_status.c#L96
                if resp.status_code == 503 and i < 2:
                    # retry
                    time.sleep(i + 1 + random.random())
                    continue

                resp.raise_for_status()
                data = resp.json()

                # successfully got a response, exit the backoff system
                break
        except Exception as e:
            self.log.error("Failed to get metrics from {}: {}".format(status_url, e))
            raise

        pool_name = data.get('pool', 'default')
        metric_tags = tags + ["pool:{0}".format(pool_name)]
        if http_host is not None:
            metric_tags += ["http_host:{0}".format(http_host)]

        for key, mname in self.GAUGES.iteritems():
            if key not in data:
                self.log.warn("Gauge metric {0} is missing from FPM status".format(key))
                continue
            self.gauge(mname, int(data[key]), tags=metric_tags)

        for key, mname in self.MONOTONIC_COUNTS.iteritems():
            if key not in data:
                self.log.warn("Counter metric {0} is missing from FPM status".format(key))
                continue
            self.monotonic_count(mname, int(data[key]), tags=metric_tags)

        # return pool, to tag the service check with it if we have one
        return pool_name

    def _process_ping(self, ping_url, ping_reply, auth, tags, pool_name, http_host, timeout, disable_ssl_validation):
        if ping_reply is None:
            ping_reply = 'pong'

        sc_tags = ["ping_url:{0}".format(ping_url)] + tags
        if http_host is not None:
            sc_tags += ["http_host:{0}".format(http_host)]

        try:
            # TODO: adding the 'full' parameter gets you per-process detailed
            # informations, which could be nice to parse and output as metrics
            resp = requests.get(ping_url, auth=auth, timeout=timeout,
                                headers=headers(self.agentConfig, http_host=http_host),
                                verify=not disable_ssl_validation)
            resp.raise_for_status()

            if ping_reply not in resp.text:
                raise Exception("Received unexpected reply to ping: {}".format(resp.text))

        except Exception as e:
            self.log.error("Failed to ping FPM pool {} on URL {}: {}".format(pool_name, ping_url, e))
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=sc_tags,
                               message=str(e))
        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=sc_tags)
