# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from six.moves.urllib.parse import quote_plus

from datadog_checks.base import OpenMetricsBaseCheckV2

from .config_models import ConfigMixin
from .constants import (
    APP_COUNT_METRIC,
    MACHINE_COUNT_METRIC,
    MACHINE_CPUS_METRIC,
    MACHINE_GPUS_METRIC,
    MACHINE_MEM_METRIC,
    MACHINE_UP_STATE,
    MACHINES_API_UP_METRIC,
)
from .metrics import METRICS, RENAME_LABELS_MAP


class FlyIoCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    DEFAULT_METRIC_LIMIT = 0
    __NAMESPACE__ = 'fly_io'

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        self.org_slug = self.instance.get('org_slug')
        default_match_string = '{__name__=~".+"}'
        self.match_string = self.instance.get('match_string', default_match_string)
        encoded_match_string = quote_plus(self.match_string)
        default_endpoint = f"https://api.fly.io/prometheus/{self.org_slug}/federate?match[]={encoded_match_string}"
        self.openmetrics_endpoint = self.instance.get('openmetrics_endpoint', default_endpoint)
        self.machines_api_endpoint = self.instance.get('machines_api_endpoint')
        self.tags = [f"fly_org:{self.org_slug}"]

        # bypass required openmetrics_endpoint
        self.instance['openmetrics_endpoint'] = self.openmetrics_endpoint

    def get_default_config(self):
        return {
            'openmetrics_endpoint': self.openmetrics_endpoint,
            'metrics': [METRICS],
            'rename_labels': RENAME_LABELS_MAP,
            'hostname_label': 'instance',
        }

    def _get_app_status(self, app_name):
        self.log.debug("Getting app status for %s", app_name)
        app_details_endpoint = f"{self.machines_api_endpoint}/v1/apps/{app_name}"
        response = self.http.get(app_details_endpoint)
        try:
            response.raise_for_status()
            app = response.json()
            app_status = app.get("status")
            return app_status
        except Exception:
            self.log.info("Failed to collect app status for app %s", app_name)
            return None

    def _submit_machine_guest_metrics(self, guest, tags, machine_id):
        self.log.debug("Getting machine guest metrics for %s", machine_id)
        num_cpus = guest.get("cpus")
        cpu_kind = guest.get("cpu_kind")
        num_gpus = guest.get("gpus")
        gpu_kind = guest.get("gpu_kind")
        memory = guest.get("memory_mb")
        if num_cpus is not None:
            additional_tags = [f"cpu_kind:{cpu_kind}"]
            self.gauge(MACHINE_CPUS_METRIC, value=num_cpus, tags=additional_tags + tags, hostname=machine_id)

        if num_gpus is not None:
            additional_tags = [f"gpu_kind:{gpu_kind}"]
            self.gauge(MACHINE_GPUS_METRIC, value=num_gpus, tags=additional_tags + tags, hostname=machine_id)

        if memory is not None:
            self.gauge(MACHINE_MEM_METRIC, value=memory, tags=tags, hostname=machine_id)

    def _collect_machines_for_app(self, app_name, app_tags):
        self.log.debug("Getting machines for app %s in org %s", app_name, self.org_slug)
        machines_endpoint = f"{self.machines_api_endpoint}/v1/apps/{app_name}/machines"
        response = self.http.get(machines_endpoint)
        response.raise_for_status()
        machines = response.json()
        external_host_tags = []
        for machine in machines:
            machine_name = machine.get("name")
            machine_state = machine.get("state")
            if machine_state != MACHINE_UP_STATE:
                self.log.info("Skipping machine %s for app %s: state is %s", machine_name, app_name, machine_state)
                continue

            machine_id = machine.get("id")
            instance_id = machine.get("instance_id")
            machine_region = machine.get("region")
            config = machine.get("config", {})
            metadata = config.get("metadata", {})
            guest = config.get("guest", {})
            fly_platform_version = metadata.get("fly_platform_version")

            machine_tags = [
                f"instance_id:{instance_id}",
                f"machine_region:{machine_region}",
                f"fly_platform_version:{fly_platform_version}",
            ]
            all_machine_tags = self.tags + machine_tags + app_tags

            self.gauge(MACHINE_COUNT_METRIC, 1, tags=all_machine_tags)
            self._submit_machine_guest_metrics(guest, self.tags, machine_id)

            external_host_tags.append((machine_id, {self.__NAMESPACE__: all_machine_tags}))

        if len(external_host_tags) > 0:
            self.set_external_tags(external_host_tags)

    def _collect_app_metrics(self):
        self.log.debug("Getting apps for org %s", self.org_slug)
        apps_endpoint = f"{self.machines_api_endpoint}/v1/apps"
        params = {'org_slug': self.org_slug}

        response = self.http.get(apps_endpoint, params=params)
        response.raise_for_status()
        apps = response.json().get("apps", [])

        for app in apps:
            app_name = app.get("name")
            self.log.debug("Processing app %s", app_name)

            app_id = app.get("id")
            app_network = app.get("network")
            app_status = self._get_app_status(app_name)
            app_base_tags = [
                f"app_id:{app_id}",
                f"app_name:{app_name}",
            ]
            app_tags = [
                f"app_status:{app_status}",
                f"app_network:{app_network}",
            ]
            self.gauge(APP_COUNT_METRIC, 1, tags=self.tags + app_base_tags + app_tags)
            self._collect_machines_for_app(app_name, app_base_tags)

    def _collect_machines_api_metrics(self):
        self.log.debug("Collecting metrics from machines api %s", self.machines_api_endpoint)
        response = self.http.get(f"{self.machines_api_endpoint}/")
        try:
            response.raise_for_status()
        except Exception as e:
            self.gauge(MACHINES_API_UP_METRIC, 0, tags=self.tags)
            self.log.error("Encountered an error hitting machines REST API %s: %s", self.machines_api_endpoint, str(e))
            raise
        self.log.debug("Connected to the machines API %s", self.machines_api_endpoint)
        self.gauge(MACHINES_API_UP_METRIC, 1, tags=self.tags)
        self._collect_app_metrics()

    def check(self, instance):
        super().check(instance)
        if self.machines_api_endpoint:
            self._collect_machines_api_metrics()
