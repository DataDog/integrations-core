# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

from six.moves.urllib.parse import urljoin, urlparse

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.utils.time import get_timestamp

from .constants import EVENT_PATH, OK_STATE, SERVERS_ENDPOINT, STATE_ENDPOINT, STATE_MAP
from .events import SilkEvent
from .metrics import BLOCKSIZE_METRICS, METRICS, READ_WRITE_METRICS


class SilkCheck(AgentCheck):

    __NAMESPACE__ = 'silk'

    STATE_SERVICE_CHECK = "system.state"
    SERVERS_SERVICE_CHECK = "server.state"
    CONNECT_SERVICE_CHECK = "can_connect"

    def __init__(self, name, init_config, instances):
        super(SilkCheck, self).__init__(name, init_config, instances)
        self.metrics_to_collect = dict(METRICS)

        server = self.instance.get("host_address")

        if server is None:
            raise ConfigurationError("host_address is a required parameter.")

        self.latest_event_query = get_timestamp()
        self.url = "{}/api/v2/".format(server)

        host = urlparse(server).netloc
        self._tags = self.instance.get("tags", []) + ["silk_host:{}".format(host)]

        if self.instance.get("enable_read_write_statistics", False):
            self.metrics_to_collect.update(dict(READ_WRITE_METRICS))

        if self.instance.get("enable_blocksize_statistics", False):
            self.metrics_to_collect.update(dict(BLOCKSIZE_METRICS))

        # System tags are collected from the /state/endpoint
        self._system_tags = []

    def check(self, _):
        # Get system state and tags
        system_tags = self.submit_system_state()

        # Submit service checks for each server
        self.submit_server_state()

        # Get events
        self.collect_events(system_tags)

        # Get metrics
        self.collect_metrics(system_tags)

        self.service_check(self.CONNECT_SERVICE_CHECK, AgentCheck.OK, tags=self._tags)

    def collect_metrics(self, system_tags):
        get_method = getattr
        for path, metrics_obj in self.metrics_to_collect.items():
            # Need to submit an object of relevant tags
            try:
                response_json, _ = self._get_data(path)
                metric_tags = self._tags + system_tags
                self.parse_metrics(
                    response_json, path, metrics_mapping=metrics_obj, get_method=get_method, tags=metric_tags
                )
            except Exception as e:
                self.log.debug("Encountered error getting Silk metrics for path %s: %s", path, str(e))

    def submit_system_state(self):
        # Get Silk State
        system_tags = []
        try:
            response_hits, code = self._get_data(STATE_ENDPOINT)
        except Exception as e:
            self.warning("Encountered error getting Silk system state: %s", str(e))
            self.service_check(self.CONNECT_SERVICE_CHECK, AgentCheck.CRITICAL, message=str(e), tags=self._tags)
            raise
        else:
            if response_hits:
                data = response_hits[0]
                state = data.get('state').lower()

                # Assign system-wide tags and metadata
                system_tags = [
                    'system_name:{}'.format(data.get('system_name')),
                    'system_id:{}'.format(data.get('system_id')),
                ]

                self._submit_version_metadata(data.get('system_version'))
                self.service_check(self.STATE_SERVICE_CHECK, STATE_MAP[state], tags=system_tags + self._tags)
            else:
                msg = (
                    "Could not access system state and version info, got response code `{}` from endpoint `{}`".format(
                        code, STATE_ENDPOINT
                    )
                )
                self.log.debug(msg)
        return system_tags

    def submit_server_state(self):
        # Get Silk State
        try:
            server_data, code = self._get_data(SERVERS_ENDPOINT)
        except Exception as e:
            self.warning("Encountered error getting Silk server state: %s", str(e))
            self.service_check(self.CONNECT_SERVICE_CHECK, AgentCheck.CRITICAL, message=str(e), tags=self._tags)
            raise
        else:
            if server_data:
                for server in server_data:
                    server_name = server.get('name')
                    tags = deepcopy(self._tags) + [
                        'server_name:{}'.format(server_name),
                    ]
                    state = server.get('status').lower()

                    if state == OK_STATE:
                        self.service_check(self.SERVERS_SERVICE_CHECK, AgentCheck.OK, tags=tags)
                    else:
                        # Other states are not documented
                        self.service_check(self.SERVERS_SERVICE_CHECK, AgentCheck.UNKNOWN, tags=tags)
                        self.log.debug("Server %s is reporting unknown status of `%s`.", server_name, state)
            else:
                msg = "Could not access server state, got response: {}".format(code)
                self.log.debug(msg)

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
                self.log.debug("Could not parse version: %s", str(e))
        else:
            self.log.debug("Could not submit version metadata, got: %s", version)

    def parse_metrics(self, output, path, tags=None, metrics_mapping=None, get_method=None):
        """
        Parse metrics from HTTP response. return_first will return the first item in `hits` key.
        """
        if not output:
            self.log.debug("No results for path %s", path)
            return

        if not tags:
            tags = self._tags

        for item in output:
            metric_tags = deepcopy(tags)

            for key, tag_name in metrics_mapping.tags.items():
                if key in item:
                    metric_tags.append("{}:{}".format(tag_name, item.get(key)))

            for key, metric in metrics_mapping.metrics.items():
                metric_part = None
                raw_metric_name, method = metric

                # read/write metrics have field_to_name
                if metrics_mapping.field_to_name:
                    for field, name_map in metrics_mapping.field_to_name.items():
                        metric_part = name_map.get(item.get(field))
                if key in item:
                    if metric_part:
                        name = "{}.{}.{}".format(metrics_mapping.prefix, metric_part, raw_metric_name)
                    else:
                        name = "{}.{}".format(metrics_mapping.prefix, raw_metric_name)

                    get_method(self, method)(name, item.get(key), tags=metric_tags)

    def _get_data(self, path):
        url = urljoin(self.url, path)
        try:
            self.log.debug("Trying to get metrics from %s", url)
            response = self.http.get(url)
            response.raise_for_status()
            response_json = response.json()
            code = response.status_code
            if response_json and 'error_msg' in response_json:
                msg = "Received error message: " + response_json.get('error_msg')
                self.log.warning(msg)
                self.service_check(self.CONNECT_SERVICE_CHECK, AgentCheck.WARNING, message=msg, tags=self._tags)
                return None, code
            return response_json.get("hits"), code
        except Exception as e:
            self.log.warning("Encountered error while getting data from %s: %s", path, str(e))
            raise

    def collect_events(self, system_tags):
        self.log.debug("Starting events collection (query start time: %s).", self.latest_event_query)

        # Get the time that events collection starts. This will be the new `self.latest_event_query` value afterwards.
        collect_events_timestamp = get_timestamp()
        try:
            event_query = EVENT_PATH.format(
                start_time=int(self.latest_event_query), end_time=int(collect_events_timestamp)
            )
            raw_events, _ = self._get_data(event_query)
            tags = self._tags + system_tags
            for event in raw_events:
                try:
                    normalized_event = SilkEvent(event, tags)
                    event_payload = normalized_event.get_datadog_payload()
                    self.event(event_payload)
                except ValueError as e:
                    self.log.error(str(e))

        except Exception as e:
            # Don't get stuck on a failure to fetch an event
            # Ignore them for next pass
            self.log.error("Unable to fetch events: %s", str(e))
        finally:
            # Update latest event query to last event time
            self.latest_event_query = collect_events_timestamp
