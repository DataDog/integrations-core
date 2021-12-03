# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

from six.moves.urllib.parse import urljoin

from datadog_checks.base import AgentCheck

from .metrics import METRICS


class SilkCheck(AgentCheck):

    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'silk'

    STATE_ENDPOINT = '/system/state'

    STATE_MAP = {'online': AgentCheck.OK, 'offline': AgentCheck.WARNING, 'degraded': AgentCheck.CRITICAL}

    STATE_SERVICE_CHECK = "state"

    def __init__(self, name, init_config, instances):
        super(SilkCheck, self).__init__(name, init_config, instances)

        server = self.instance.get("server")
        port = self.instance.get("port", 443)
        self.url = "{}:{}/api/v2".format(server, port)
        self.tags = self.instance.get("tags", [])

    def check(self, _):
        try:
            response_json = self.get_metrics(self.STATE_ENDPOINT)
        except Exception as e:
            self.log.debug("Encountered error getting Silk state: %s" % str(e))
            self.service_check("can_connect", AgentCheck.CRITICAL, message=str(e))
        else:
            if response_json:
                data = self.parse_metrics(response_json, self.STATE_ENDPOINT, return_first=True)
                state = data.get('state').lower()
                self.service_check(self.STATE_SERVICE_CHECK, self.STATE_MAP[state])

        get_method = getattr
        for path, metrics_obj in METRICS.items():
            # Need to submit an object of relevant tags
            response_json = self.get_metrics(path)
            self.parse_metrics(response_json, path, metrics_obj, get_method)

    def parse_metrics(self, output, path, metrics_mapping=None, get_method=None, return_first=False):
        """
        Parse metrics from HTTP response. return_first will return the first item in `hits` key.
        """
        if not output:
            self.log.debug("No results for path %s"% path)
            return

        hits = output.get('hits')

        if return_first:
            return hits[0]

        for item in hits:
            metric_tags = deepcopy(self.tags)
            for key, tag_name in metrics_mapping.tags.items():
                if key in item:
                    metric_tags.append("{}:{}".format(tag_name, item.get(key)))

            for key, metric in metrics_mapping.metrics.items():
                metric_name, method = metric
                if key in item:
                    get_method(self, method)(
                        "{}.{}".format(metrics_mapping.prefix, metric_name), item.get(key), tags=metric_tags
                    )

    def get_metrics(self, path):
        try:
            response = self.http.get(urljoin(self.url, path))
            response.raise_for_status()
            response_json = response.json()
            return response_json
        except Exception as e:
            self.log.debug("Encountered error while getting metrics from %s: %s" % (path, str(e)))
            return None
