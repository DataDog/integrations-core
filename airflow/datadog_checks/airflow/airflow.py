# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import requests

from datadog_checks.base import AgentCheck, ConfigurationError

AIRFLOW_STATUS_OK = "OK"


class AirflowCheck(AgentCheck):
    def __init__(self, name, init_config, instances):
        super(AirflowCheck, self).__init__(name, init_config, instances)

        self._url = self.instance.get('url', '')
        self._tags = self.instance.get('tags', [])

        # The Agent only makes one attempt to instantiate each AgentCheck so any errors occurring
        # in `__init__` are logged just once, making it difficult to spot. Therefore, we emit
        # potential configuration errors as part of the check run phase.
        # The configuration is only parsed once if it succeed, otherwise it's retried.
        self.check_initializations.append(self._parse_config)

    def check(self, _):
        tags = ['url:{}'.format(self._url)] + self._tags
        url = self._url + "/api/experimental/test"

        resp = self._get_json(url)

        if resp is None:
            can_connect_status = AgentCheck.CRITICAL
        else:
            can_connect_status = AgentCheck.OK

        self.service_check('airflow.can_connect', can_connect_status, tags=tags)
        self.gauge('airflow.can_connect', int(can_connect_status == AgentCheck.OK), tags=tags)

        if resp is not None:
            if resp.get('status') == AIRFLOW_STATUS_OK:
                health_status = AgentCheck.OK
            else:
                health_status = AgentCheck.CRITICAL

            self.service_check('airflow.healthy', health_status, tags=tags)
            self.gauge('airflow.healthy', int(health_status == AgentCheck.OK), tags=tags)

    def _parse_config(self):
        if not self._url:
            raise ConfigurationError('Missing configuration: url')

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
