# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six.moves.urllib.parse import urljoin

from datadog_checks.base import AgentCheck


class SilkCheck(AgentCheck):

    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'silk'

    ENDPOINTS = [
        '/hosts',
        '/stats/system',
        '/stats/volumes',
        '/volumes',
    ]

    STATE_ENDPOINT = '/system/state'

    STATE_MAP = {'online': AgentCheck.OK, 'offline': AgentCheck.WARNING, 'degraded': AgentCheck.CRITICAL}

    STATE_SERVICE_CHECK = "state"

    def __init__(self, name, init_config, instances):
        super(SilkCheck, self).__init__(name, init_config, instances)

        server = self.instance.get("server")
        port = self.instance.get("port", 443)
        self.url = "{}:{}/api/v2".format(server, port)

    def check(self, _):
        try:
            response = self.get_metrics(self.STATE_ENDPOINT)
            response.raise_for_status()
            response_json = response.json()
        except Exception as e:
            self.service_check("can_connect", AgentCheck.CRITICAL, message=str(e))
        else:
            if response_json:
                data = self.parse_metrics(response_json, self.STATE_ENDPOINT, return_first=True)
                state = data.get('state').lower()
                self.service_check(self.STATE_SERVICE_CHECK, state)

        for path in self.ENDPOINTS:
            # Need to submit an object of relevant tags
            response_json = self.get_metrics(path)
            self.parse_metrics(response_json, path)

    def parse_metrics(self, output, path, return_first=False):
        """
        Parse metrics from HTTP response. return_first will return the first item in `hits` key.
        """
        if not output:
            self.log.debug("No results for path {}".format(path))
            return

        hits = output.get('hits')

        if return_first:
            return hits[0]

        # Parse metrics at some point here. Establish a system to reuse with any path
        for item in hits:
            for key, value in item.items():
                if isinstance(value, (int, float)):
                    self.gauge(key, value, tags=['path:{}'.format(path)])

    def get_metrics(self, path):
        try:
            response = self.http.get(urljoin(self.url, path))
            response.raise_for_status()
            response_json = response.json()
            return response_json
        except Exception as e:
            self.log.debug("Encountered error while getting metrics from {}: {}".format(path, str(e)))
            return None
