# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from urllib.parse import quote_plus

from datadog_checks.base import OpenMetricsBaseCheckV2

from .config_models import ConfigMixin
from .constants import (
    APP_COUNT_METRIC,
    MACHINE_COUNT_METRIC,
    MACHINE_CPUS_METRIC,
    MACHINE_GPUS_METRIC,
    MACHINE_MEM_METRIC,
    MACHINE_SWAP_SIZE_METRIC,
    MACHINE_UP_STATE,
    MACHINES_API_UP_METRIC,
    VOLUME_BLOCK_SIZE_METRIC,
    VOLUME_BLOCKS_AVAIL_METRIC,
    VOLUME_BLOCKS_FREE_METRIC,
    VOLUME_BLOCKS_METRIC,
    VOLUME_CREATED_METRIC,
    VOLUME_CREATED_STATE,
    VOLUME_ENCRYPTED_METRIC,
    VOLUME_SIZE_METRIC,
)
from .errors import handle_error
from .metrics import HISTOGRAM_METRICS, METRICS, RENAME_LABELS_MAP


class FlyIoCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    DEFAULT_METRIC_LIMIT = 0
    __NAMESPACE__ = 'fly_io'

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        self.org_slug = self.instance.get('org_slug')
        self.machines_api_endpoint = self.instance.get('machines_api_endpoint')
        self.tags = [f"fly_org:{self.org_slug}"]
        match_string = self.instance.get('match_string', '{__name__=~".+"}')
        encoded_match_string = quote_plus(match_string)
        default_endpoint = f"https://api.fly.io/prometheus/{self.org_slug}/federate?match[]={encoded_match_string}"
        self.openmetrics_endpoint = self.instance.get('openmetrics_endpoint', default_endpoint)
        self.instance['openmetrics_endpoint'] = self.openmetrics_endpoint
        self.check_initializations.append(self.configure_additional_transformers)

    def get_default_config(self):

        return {
            'openmetrics_endpoint': self.openmetrics_endpoint,
            'metrics': [METRICS],
            'rename_labels': RENAME_LABELS_MAP,
            'hostname_label': 'instance',
        }

    def configure_additional_transformers(self):
        metric_transformer = self.scrapers[self.openmetrics_endpoint].metric_transformer
        metric_transformer.add_custom_transformer(
            '|'.join(f'{metric}' for metric in HISTOGRAM_METRICS.keys()),
            self.configure_histogram_transformer(),
            pattern=True,
        )

    def configure_histogram_transformer(self):
        def histogram_transformer(metric, sample_data, _runtime_data):
            metric_remapped = HISTOGRAM_METRICS[metric.name]
            for sample, tags, hostname in sample_data:
                self.count(metric_remapped, sample.value, tags=tags, hostname=hostname)

        return histogram_transformer

    @handle_error
    def _get_app_status(self, app_name):
        self.log.debug("Getting app status for %s", app_name)
        app_details_endpoint = f"{self.machines_api_endpoint}/v1/apps/{app_name}"
        response = self.http.get(app_details_endpoint)
        response.raise_for_status()
        app = response.json()
        app_status = app.get("status")
        return app_status

    @handle_error
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

    @handle_error
    def _submit_machine_init_metrics(self, machine_init, tags, machine_id):
        self.log.debug("Getting machine init metrics for %s", machine_id)
        swap_size_mb = machine_init.get("swap_size_mb")
        if swap_size_mb is not None:
            self.gauge(MACHINE_SWAP_SIZE_METRIC, value=swap_size_mb, tags=tags, hostname=machine_id)

    @handle_error
    def _collect_volumes_for_app(self, app_name, app_tags):
        self.log.debug("Getting volumes for app %s in org %s", app_name, self.org_slug)
        volumes_endpoint = f"{self.machines_api_endpoint}/v1/apps/{app_name}/volumes"
        response = self.http.get(volumes_endpoint)
        response.raise_for_status()
        volumes = response.json()
        self.log.debug("Collected %s volumes for app %s in org %s", len(volumes), app_name, self.org_slug)
        for volume in volumes:
            volume_id = volume.get("id")
            volume_name = volume.get("name")
            region = volume.get("region")
            zone = volume.get("zone")
            fstype = volume.get("fstype")
            attached_machine_id = volume.get("attached_machine_id")
            volume_tags = [
                f"volume_id:{volume_id}",
                f"volume_name:{volume_name}",
                f"fly_region:{region}",
                f"fly_zone:{zone}",
                f"fstype:{fstype}",
                f"attached_machine_id:{attached_machine_id}",
                f"app_name:{app_name}",
            ]
            all_tags = self.tags + volume_tags

            state = volume.get("state")
            size_gb = volume.get("size_gb")
            encrypted = volume.get("encrypted")
            blocks = volume.get("blocks")
            block_size = volume.get("block_size")
            blocks_free = volume.get("blocks_free")
            blocks_avail = volume.get("blocks_avail")

            was_created = 1 if state == VOLUME_CREATED_STATE else 0
            self.gauge(VOLUME_CREATED_METRIC, value=was_created, tags=all_tags)

            encrypted = int(encrypted) if encrypted is not None else 0
            self.gauge(VOLUME_ENCRYPTED_METRIC, value=encrypted, tags=all_tags)

            if size_gb is not None:
                self.gauge(VOLUME_SIZE_METRIC, value=size_gb, tags=all_tags)

            if blocks is not None:
                self.gauge(VOLUME_BLOCKS_METRIC, value=blocks, tags=all_tags)

            if block_size is not None:
                self.gauge(VOLUME_BLOCK_SIZE_METRIC, value=block_size, tags=all_tags)

            if blocks_free is not None:
                self.gauge(VOLUME_BLOCKS_FREE_METRIC, value=blocks_free, tags=all_tags)

            if blocks_avail is not None:
                self.gauge(VOLUME_BLOCKS_AVAIL_METRIC, value=blocks_avail, tags=all_tags)

    @handle_error
    def _collect_machines_for_app(self, app_name, app_tags):
        self.log.debug("Getting machines for app %s in org %s", app_name, self.org_slug)
        machines_endpoint = f"{self.machines_api_endpoint}/v1/apps/{app_name}/machines"
        response = self.http.get(machines_endpoint)
        response.raise_for_status()
        machines = response.json()
        external_host_tags = []
        self.log.debug("Collected %s machines for app %s in org %s", len(machines), app_name, self.org_slug)

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
            machine_init = config.get("init", {})
            fly_platform_version = metadata.get("fly_platform_version")

            machine_tags = [
                f"instance_id:{instance_id}",
                f"machine_region:{machine_region}",
                f"fly_platform_version:{fly_platform_version}",
            ]
            all_machine_tags = self.tags + machine_tags + app_tags

            self.gauge(MACHINE_COUNT_METRIC, 1, tags=all_machine_tags)
            self._submit_machine_guest_metrics(guest, self.tags, machine_id)
            self._submit_machine_init_metrics(machine_init, self.tags, machine_id)

            external_host_tags.append((machine_id, {self.__NAMESPACE__: all_machine_tags}))

        if len(external_host_tags) > 0:
            self.set_external_tags(external_host_tags)

    @handle_error
    def _collect_app_metrics(self, apps_data):
        self.log.debug("Getting apps for org %s", self.org_slug)
        apps = apps_data.get("apps", [])

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
            self._collect_volumes_for_app(app_name, app_base_tags)

    def _collect_machines_api_metrics(self):
        self.log.debug("Collecting metrics from machines api %s", self.machines_api_endpoint)
        params = {'org_slug': self.org_slug}
        response = self.http.get(f"{self.machines_api_endpoint}/v1/apps", params=params)
        apps_data = None
        try:
            response.raise_for_status()
            apps_data = response.json()
        except Exception as e:
            self.gauge(MACHINES_API_UP_METRIC, 0, tags=self.tags)
            self.log.error("Encountered an error hitting machines REST API %s: %s", self.machines_api_endpoint, str(e))
            raise

        self.log.debug("Connected to the machines API %s", self.machines_api_endpoint)
        self.gauge(MACHINES_API_UP_METRIC, 1, tags=self.tags)
        self._collect_app_metrics(apps_data)

    def check(self, instance):
        super().check(instance)
        if self.machines_api_endpoint:
            self._collect_machines_api_metrics()
