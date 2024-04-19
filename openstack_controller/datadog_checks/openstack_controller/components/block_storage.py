# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from datadog_checks.openstack_controller.components.component import Component
from datadog_checks.openstack_controller.metrics import (
    CINDER_CLUSTER_COUNT,
    CINDER_CLUSTER_METRICS,
    CINDER_CLUSTER_PREFIX,
    CINDER_CLUSTER_TAGS,
    CINDER_METRICS_PREFIX,
    CINDER_POOL_COUNT,
    CINDER_POOL_METRICS,
    CINDER_POOL_PREFIX,
    CINDER_POOL_TAGS,
    CINDER_RESPONSE_TIME,
    CINDER_SERVICE_CHECK,
    CINDER_SNAPSHOT_COUNT,
    CINDER_SNAPSHOT_METRICS,
    CINDER_SNAPSHOT_PREFIX,
    CINDER_SNAPSHOT_TAGS,
    CINDER_TRANSFER_COUNT,
    CINDER_TRANSFER_TAGS,
    CINDER_VOLUME_COUNT,
    CINDER_VOLUME_METRICS,
    CINDER_VOLUME_PREFIX,
    CINDER_VOLUME_TAGS,
    get_metrics_and_tags,
)


class BlockStorage(Component):
    ID = Component.Id.BLOCK_STORAGE
    TYPES = Component.Types.BLOCK_STORAGE
    SERVICE_CHECK = CINDER_SERVICE_CHECK

    def __init__(self, check):
        super(BlockStorage, self).__init__(check)

    @Component.register_global_metrics(ID)
    @Component.http_error(report_service_check=True)
    def _report_response_time(self, global_components_config, tags):
        self.check.log.debug("reporting `%s` response time", BlockStorage.ID.value)
        response_time = self.check.api.get_response_time(BlockStorage.TYPES.value)
        self.check.log.debug("`%s` response time: %s", BlockStorage.ID.value, response_time)
        self.check.gauge(CINDER_RESPONSE_TIME, response_time, tags=tags)

    @Component.register_project_metrics(ID)
    @Component.http_error()
    def _report_volumes(self, project_id, tags, config):
        report_volumes = config.get('volumes', True)
        if report_volumes:
            data = self.check.api.get_block_storage_volumes(project_id)
            for item in data:
                volume = get_metrics_and_tags(
                    item,
                    tags=CINDER_VOLUME_TAGS,
                    prefix=CINDER_VOLUME_PREFIX,
                    metrics=CINDER_VOLUME_METRICS,
                )
                self.check.log.debug("volume: %s", volume)
                self.check.gauge(CINDER_VOLUME_COUNT, 1, tags=tags + volume['tags'])
                for metric, value in volume['metrics'].items():
                    self.check.gauge(metric, value, tags=tags + volume['tags'])

    @Component.register_project_metrics(ID)
    @Component.http_error()
    def _report_transfers(self, project_id, tags, config):
        report_transfers = config.get('transfers', True)
        if report_transfers:
            data = self.check.api.get_block_storage_transfers(project_id)
            for item in data:
                transfer = get_metrics_and_tags(
                    item,
                    tags=CINDER_TRANSFER_TAGS,
                    prefix=CINDER_METRICS_PREFIX,
                    metrics=[CINDER_TRANSFER_COUNT],
                )
                self.check.log.debug("transfer: %s", transfer)
                self.check.gauge(CINDER_TRANSFER_COUNT, 1, tags=tags + transfer['tags'])

    @Component.register_project_metrics(ID)
    @Component.http_error()
    def _report_snapshots(self, project_id, tags, config):
        report_snapshots = config.get('snapshots', True)
        if report_snapshots:
            data = self.check.api.get_block_storage_snapshots(project_id)
            for item in data:
                snapshot = get_metrics_and_tags(
                    item,
                    tags=CINDER_SNAPSHOT_TAGS,
                    prefix=CINDER_SNAPSHOT_PREFIX,
                    metrics=CINDER_SNAPSHOT_METRICS,
                )
                self.check.log.debug("snapshot: %s", snapshot)
                self.check.gauge(CINDER_SNAPSHOT_COUNT, 1, tags=tags + snapshot['tags'])
                for metric, value in snapshot['metrics'].items():
                    self.check.gauge(metric, value, tags=tags + snapshot['tags'])

    @Component.register_project_metrics(ID)
    @Component.http_error()
    def _report_pools(self, project_id, tags, config):
        report_pools = config.get('pools', True)
        if report_pools:
            data = self.check.api.get_block_storage_pools(project_id)
            for item in data:
                pool = get_metrics_and_tags(
                    item,
                    tags=CINDER_POOL_TAGS,
                    prefix=CINDER_POOL_PREFIX,
                    metrics=CINDER_POOL_METRICS,
                )
                self.check.log.debug("pool: %s", pool)
                self.check.gauge(CINDER_POOL_COUNT, 1, tags=tags + pool['tags'])
                for metric, value in pool['metrics'].items():
                    self.check.gauge(metric, value, tags=tags + pool['tags'])

    @Component.register_project_metrics(ID)
    @Component.http_error()
    def _report_clusters(self, project_id, tags, config):
        report_clusters = config.get('clusters', True)
        if report_clusters:
            data = self.check.api.get_block_storage_clusters(project_id)
            for item in data:
                cluster = get_metrics_and_tags(
                    item,
                    tags=CINDER_CLUSTER_TAGS,
                    prefix=CINDER_CLUSTER_PREFIX,
                    metrics=CINDER_CLUSTER_METRICS,
                )
                self.check.log.debug("cluster: %s", cluster)
                self.check.gauge(CINDER_CLUSTER_COUNT, 1, tags=tags + cluster['tags'])
                for metric, value in cluster['metrics'].items():
                    self.check.gauge(metric, value, tags=tags + cluster['tags'])
