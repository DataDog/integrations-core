# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

from six.moves.urllib.parse import urljoin

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.time import get_timestamp

from .events import SilkEvent
from .metrics import METRICS

EVENT_PATH = "events?timestamp__gte={}"


class SilkCheck(AgentCheck):

    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'silk'

    STATE_ENDPOINT = 'system/state'

    STATE_MAP = {'online': AgentCheck.OK, 'offline': AgentCheck.WARNING, 'degraded': AgentCheck.CRITICAL}

    STATE_SERVICE_CHECK = "state"
    CONNECT_SERVICE_CHECK = "can_connect"

    def __init__(self, name, init_config, instances):
        super(SilkCheck, self).__init__(name, init_config, instances)

        server = self.instance.get("host_address")
        self.latest_event_query = int(get_timestamp())
        self.url = "{}/api/v2/".format(server)
        self.tags = self.instance.get("tags", [])
        self._host_tags = []

    def check(self, _):
        # Get system state
        self.submit_state()

        # Get events
        self.collect_events()

        # Get metrics
        get_method = getattr
        for path, metrics_obj in METRICS.items():
            # Need to submit an object of relevant tags
            try:
                response_json, _ = self._get_data(path)
                self.parse_metrics(response_json, path, metrics_obj, get_method)
            except Exception as e:
                self.log.debug("Encountered error getting Silk metrics for path %s: %s", path, str(e))
        self.service_check(self.CONNECT_SERVICE_CHECK, AgentCheck.OK, tags=self.tags)


    def submit_state(self):
        # Get Silk State
        try:
            response_json, code = self._get_data(self.STATE_ENDPOINT)
        except Exception as e:
            self.warning("Encountered error getting Silk state: %s", str(e))
            self.service_check(self.CONNECT_SERVICE_CHECK, AgentCheck.CRITICAL, message=str(e), tags=self.tags)
            self.service_check(self.STATE_SERVICE_CHECK, AgentCheck.UNKNOWN, message=str(e), tags=self.tags)
            raise
        else:
            if response_json:
                if 'error_msg' in response_json:
                    msg = "Received error message: %s", response_json.get('error_msg')
                    self.log.warning(msg)
                    self.service_check(self.STATE_SERVICE_CHECK, AgentCheck.WARNING, message=msg, tags=self.tags)
                    return
                data = self.parse_metrics(response_json, self.STATE_ENDPOINT, return_first=True)
                state = data.get('state').lower()

                # Assign system-wide tags and metadata
                self._assign_host_tags(data)
                self._submit_version_metadata(data.get('system_version'))
                self.service_check(self.STATE_SERVICE_CHECK, self.STATE_MAP[state], tags=self.tags)
            else:
                msg = "Could not access system state, got response: {}".format(code)
                self.service_check(self.STATE_SERVICE_CHECK, AgentCheck.UNKNOWN, message=msg, tags=self.tags)
                return

    @AgentCheck.metadata_entrypoint
    def _submit_version_metadata(self, version):
        if version:
            try:
                # "system_version":"6.0.102.25"
                major, minor, patch, release = version.split(".")

                version_parts = {
                    'major': str(int(major)),
                    'minor': str(int(minor)),
                    'patch': str(int(patch)),
                    'release': str(int(release)),
                }
                self.set_metadata('version', version, scheme='parts', part_map=version_parts)
            except Exception as e:
                self.log.debug("Could not parse version: %", str(e))
        else:
            self.log.debug("Could not submit version metadata, got: %", version)

    def _assign_host_tags(self, state_data):

        system_name = state_data.get('system_name')
        system_id = state_data.get('system_id')

    def parse_metrics(self, output, path, metrics_mapping=None, get_method=None, return_first=False):
        """
        Parse metrics from HTTP response. return_first will return the first item in `hits` key.
        """
        if not output:
            self.log.debug("No results for path %s", path)
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

    def _get_data(self, path):
        url = urljoin(self.url, path)
        try:
            self.log.debug("Trying to get metrics from %s", url)
            response = self.http.get(url)
            response.raise_for_status()
            response_json = response.json()
            code = response.status_code
            return response_json, code
        except Exception as e:
            self.log.debug("Encountered error while getting metrics from %s: %s", path, str(e))
            raise

    def collect_events(self):
        self.log.debug("Starting events collection (query start time: %s).", self.latest_event_query)
        latest_event_time = None
        collect_events_start_time = get_timestamp()
        try:
            event_query = EVENT_PATH.format(self.latest_event_query)
            response_json, code = self._get_data(event_query)
            raw_events = response_json.get("hits")

            for event in raw_events:
                normalized_event = SilkEvent(event, self.tags)
                event_payload = normalized_event.get_datadog_payload()
                if event_payload is not None:
                    self.event(event_payload)
                if latest_event_time is None or event_payload.get("timestamp") > latest_event_time:
                    latest_event_time = event_payload.get("timestamp")

        except Exception as e:
            # Don't get stuck on a failure to fetch an event
            # Ignore them for next pass
            self.log.warning("Unable to fetch Events: %s", str(e))

        if latest_event_time is not None:
            self.latest_event_query = int(latest_event_time)
        else:
            # In case no events were collected
            self.latest_event_query = int(collect_events_start_time)
