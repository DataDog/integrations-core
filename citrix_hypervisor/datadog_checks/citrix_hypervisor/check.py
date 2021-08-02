# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

import demjson

from datadog_checks.base import AgentCheck

# from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout
# from json import JSONDecodeError


class CitrixHypervisorCheck(AgentCheck):
    __NAMESPACE__ = "citrix_hypervisor"

    def __init__(self, name, init_config, instances):
        super(CitrixHypervisorCheck, self).__init__(name, init_config, instances)

        self._last_timestamp = 0
        self._base_url = self.instance['url'].rstrip('/')

        self.check_initializations.append(self._check_connection)

    def _check_connection(self):
        self.log.warning("Check initialization. Verifying connection and getting latest timestamp")

        # Get the latest timestamp to reduce the length of the update endpoint response
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
            r = self.http.get(self._base_url + '/rrd_updates', params=params)
            r.raise_for_status()
            # Response is not formatted for simplejson, it's missing double quotes " around the field names
            data = demjson.decode(r.content)

            self._last_timestamp = int(data['meta']['end'])

            return data
        except Exception as e:
            self.log.exception(e)

    def submit_metrics(self, data):
        legends = data['meta']['legend']
        values = data['data'][0]['values']
        for i in range(len(legends)):
            # TODO
            metric_name = legends[i].split(':')[-1]
            self.gauge('host.{}'.format(metric_name), values[i])

    def check(self, _):
        # type: (Any) -> None
        data = self._get_updated_metrics()

        # TODO: submit metric from data
        self.submit_metrics(data)

    @AgentCheck.metadata_entrypoint
    def collect_hypervisor_version(self):
        # TODO: send version
        pass
