# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict, List

import yaml

from datadog_checks.base import AgentCheck, ConfigurationError

from .metrics import build_metric

# from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout
# from json import JSONDecodeError


class CitrixHypervisorCheck(AgentCheck):
    __NAMESPACE__ = 'citrix_hypervisor'
    SERVICE_CHECK_CONNECT = 'can_connect'

    def __init__(self, name, init_config, instances):
        # type: (str, Dict, List[Dict]) -> None
        super(CitrixHypervisorCheck, self).__init__(name, init_config, instances)

        self._last_timestamp = 0

        if self.instance.get('url') is None:
            raise ConfigurationError('Missing configuration option: url')
        self._base_url = self.instance['url'].rstrip('/')

        self.tags = self.instance.get('tags', [])

        self.check_initializations.append(self._check_connection)

    def _check_connection(self):
        # type: () -> None
        # Get the latest timestamp to reduce the length of the update endpoint response
        r = self.http.get(self._base_url + '/host_rrd', params={'json': 'true'})
        r.raise_for_status()
        self._last_timestamp = int(float(r.json()['lastupdate'])) - 60

    def _get_updated_metrics(self):
        # type: () -> Dict
        params = {
            'start': self._last_timestamp,
            'host': 'true',
            'json': 'true',
            'cf': 'AVERAGE|MIN|MAX',
        }
        r = self.http.get(self._base_url + '/rrd_updates', params=params)
        r.raise_for_status()
        # Response is not formatted for simplejson, it's missing double quotes " around the field names
        data = yaml.safe_load(r.content)

        if data['meta'].get('end') is not None:
            self._last_timestamp = int(data['meta']['end'])
        else:
            for key in data['meta'].keys():
                if data['meta'][key] is None and key.startswith('end'):
                    self._last_timestamp = int(key.split(':')[-1])

        return data

    def submit_metrics(self, data):
        # type: (Dict) -> None
        legends = data['meta']['legend']
        values = data['data'][0]['values']
        for i in range(len(legends)):
            # TODO
            metric_name, tags = build_metric(legends[i], self.log)

            if metric_name is not None:
                self.gauge(metric_name, values[i], tags=self.tags + tags)

    def check(self, _):
        # type: (Any) -> None
        try:
            data = self._get_updated_metrics()

            self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, self.tags)
        except Exception as e:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.CRITICAL, self.tags)
            self.log.exception(e)
        else:
            self.submit_metrics(data)

    @AgentCheck.metadata_entrypoint
    def collect_hypervisor_version(self):
        # type: () -> None
        # TODO: send version
        pass
