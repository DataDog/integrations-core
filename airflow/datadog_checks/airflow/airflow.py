# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import requests

from datadog_checks.base import AgentCheck, ConfigurationError


class AirflowCheck(AgentCheck):
    def check(self, instance):
        tags = instance.get('tags', [])

        base_url = instance.get('url')
        if not base_url:
            raise ConfigurationError('Missing configuration: url')

        self._submit_health_status(base_url, tags)

    def _submit_health_status(self, base_url, base_tags):
        url = base_url + "/api/experimental/test"
        tags = ['url:{}'.format(url)] + base_tags

        resp = self._get_json(url)

        if resp is not None:
            can_connect_status = AgentCheck.OK
        else:
            can_connect_status = AgentCheck.CRITICAL

        self.service_check('airflow.can_connect', can_connect_status, tags=tags)
        self.gauge('airflow.can_connect', int(can_connect_status == AgentCheck.OK), tags=tags)

    def _get_json(self, url):
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
        return None
