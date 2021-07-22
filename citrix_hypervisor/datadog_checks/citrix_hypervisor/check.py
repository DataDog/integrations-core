# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

from datadog_checks.base import AgentCheck

# from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout
# from json import JSONDecodeError


class CitrixHypervisorCheck(AgentCheck):
    __NAMESPACE__ = "citrix_hypervisor"

    def __init__(self, name, init_config, instances):
        super(CitrixHypervisorCheck, self).__init__(name, init_config, instances)

        self._base_url = self.instance['url'].rstrip('/')

        self.check_initializations.append(self._check_connection)


    def _check_connection(self):
        self.log.warning("Check initialization. Verifying connection and getting latest timestamp")

        r = self.http.get(self._base_url + '/host_rrd', params={'json': 'true'})
        r.raise_for_status()
        self._last_timestamp = int(float(r.json()['lastupdate'])) - 60

    def _get_updated_metrics(self):
        try:
            params = {
                'start': self._last_timestamp,
                'host': 'true',
                'json': 'true',
                'cf': 'AVERAGE|MIN|MAX',
            }
            self.log.warning("Sending get request to " + self._base_url + '/rrd_updates')
            r = self.http.get(self._base_url + '/rrd_updates', params=params)
            r.raise_for_status()
            data = r.json()

            self._last_timestamp = int(data['meta']['end'])

            return data
        except Exception as e:
            self.log.exception(e)

    def check(self, _):
        # type: (Any) -> None
        data = self._get_updated_metrics()

        # TODO: submit metric from data
        self.gauge('host.{}'.format(data['meta']['legend'][0].split(':')[-1]), data['data'][0]['values'][0])

    @AgentCheck.metadata_entrypoint
    def collect_hypervisor_version(self):
        # TODO: send version
        pass
