# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import requests

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.errors import CheckException


class DruidCheck(AgentCheck):
    def check(self, _):
        custom_tags = self.instance.get('tags', [])

        base_url = self.instance.get('url')
        if not base_url:
            raise ConfigurationError('Missing configuration: url')

        process_properties = self._get_process_properties(base_url, custom_tags)

        druid_service = process_properties['druid.service']
        tags = custom_tags + ['druid_service:{}'.format(druid_service)]

        self._submit_health_status(base_url, tags)

    def _submit_health_status(self, base_url, base_tags):
        url = base_url + "/status/health"
        tags = ['url:{}'.format(url)] + base_tags

        resp = self._make_request(url)

        if resp is True:
            status = AgentCheck.OK
            health_value = 1
        else:
            status = AgentCheck.CRITICAL
            health_value = 0

        self.service_check('druid.service.health', status, tags=tags)
        self.gauge('druid.service.health', health_value, tags=tags)

    def _get_process_properties(self, base_url, tags):
        url = base_url + "/status/properties"
        service_check_tags = ['url:{}'.format(url)] + tags

        resp = self._make_request(url)

        if resp is None:
            status = AgentCheck.CRITICAL
        else:
            status = AgentCheck.OK

        self.service_check('druid.service.can_connect', status, tags=service_check_tags)

        if resp is None:
            raise CheckException("Unable to retrieve Druid service properties at {}".format(url))
        return resp

    def _make_request(self, url):
        try:
            resp = self.http.get(url)
            resp.raise_for_status()
            return resp.json()
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as e:
            self.warning(
                "Couldn't connect to URL: %s with exception: %s. Please verify the address is reachable", url, e
            )
        except requests.exceptions.Timeout as e:
            self.warning("Connection timeout when connecting to %s: %s", url, e)
