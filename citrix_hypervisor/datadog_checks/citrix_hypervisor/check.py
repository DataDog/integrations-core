# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict, List, Optional

import yaml
from six.moves import xmlrpc_client as xmlrpclib

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
        self.xenserver = None

        self.check_initializations.append(self._check_connection)

    def _check_connection(self):
        # type: () -> None
        # Get the latest timestamp to reduce the length of the update endpoint response
        r = self.http.get(self._base_url + '/host_rrd', params={'json': 'true'})
        if r.status_code == 200:
            self._last_timestamp = int(float(r.json()['lastupdate'])) - 60
        else:
            self.log.warning("Couldn't initialize the timestamp due to HTTP error %s, set it to 0", r.reason)

        try:
            self.xenserver = xmlrpclib.Server(self._base_url)
        except Exception as e:
            self.log.warning(str(e))

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
                self.gauge(metric_name, values[i], tags=self.tags + self._additional_tags + tags)

    def open_session(self):
        # type: () -> Optional[Dict[str, str]]
        if self.xenserver is None:
            return None

        session = self.xenserver.session.login_with_password(
            self.instance.get('username', ''), self.instance.get('password', '')
        )

        if session.get('Status') == 'Failure':
            if 'HOST_IS_SLAVE' in session.get('ErrorDescription', []):
                self._additional_tags.append('server_type:slave')
            return None

        self._additional_tags.append('server_type:master')

        return session

    def check(self, _):
        # type: (Any) -> None
        self._additional_tags = []  # type: List[str]
        session = self.open_session()

        try:
            data = self._get_updated_metrics()

            self.service_check(
                self.SERVICE_CHECK_CONNECT,
                self.OK,
                ['citrix_hypervisor_url:{}'.format(self._base_url)] + self._additional_tags + self.tags,
            )
        except Exception as e:
            self.service_check(
                self.SERVICE_CHECK_CONNECT,
                self.CRITICAL,
                ['citrix_hypervisor_url:{}'.format(self._base_url)] + self._additional_tags + self.tags,
            )
            self.log.exception(e)
        else:
            self.submit_metrics(data)

        if session is not None:
            self.xenserver.session.logout(session.get('Value'))
