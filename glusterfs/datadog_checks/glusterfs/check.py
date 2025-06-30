# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from typing import Dict, List  # noqa: F401

from datadog_checks.base import AgentCheck
from datadog_checks.base.config import is_affirmative

from .glusterlib.cluster import Cluster
from .metrics import BRICK_STATS, CLUSTER_STATS, PARSE_METRICS, VOL_SUBVOL_STATS, VOLUME_STATS

GLUSTER_VERSION = 'glfs_version'
CLUSTER_STATUS = 'cluster_status'


class GlusterfsCheck(AgentCheck):
    __NAMESPACE__ = 'glusterfs'

    CLUSTER_SC = "cluster.health"
    VOLUME_SC = "volume.health"
    BRICK_SC = "brick.health"

    def __init__(self, name, init_config, instances):
        # type: (str, Dict, List[Dict]) -> None
        super(GlusterfsCheck, self).__init__(name, init_config, instances)
        self._tags = self.instance.get('tags', [])
        self.use_sudo = is_affirmative(self.instance.get('use_sudo', True))

    def check(self, _):
        raise Exception("LOL")
        gstatus = json.loads(self.get_gstatus_data())
        if 'data' in gstatus:
            data = gstatus['data']
            self.submit_metrics(data, 'cluster', CLUSTER_STATS, self._tags)

            self.submit_version_metadata(data)

            volume_info = data.get('volume_summary', [])
            self.parse_volume_summary(volume_info)

            if CLUSTER_STATUS in data:
                status = data[CLUSTER_STATUS].lower()
                if status == 'healthy':
                    self.service_check(self.CLUSTER_SC, AgentCheck.OK, tags=self._tags)
                elif status == 'degraded':
                    self.service_check(
                        self.CLUSTER_SC, AgentCheck.CRITICAL, tags=self._tags, message="Cluster status is %s" % status
                    )
                else:
                    self.service_check(
                        self.CLUSTER_SC, AgentCheck.WARNING, tags=self._tags, message="Cluster status is %s" % status
                    )
        else:
            self.log.warning("No data from gstatus: %s", gstatus)

    @AgentCheck.metadata_entrypoint
    def submit_version_metadata(self, data):
        raw_version = data.get(GLUSTER_VERSION)
        if not raw_version:
            self.log.warning('Could not retrieve GlusterFS version info: %s', raw_version)
            return

        self.log.debug('Found GlusterFS version: %s', raw_version)
        try:
            major, minor, patch = self.parse_version(raw_version)
            version_parts = {'major': str(int(major)), 'minor': str(int(minor))}
            if patch:
                version_parts['patch'] = str(int(patch))
            self.set_metadata('version', raw_version, scheme='parts', part_map=version_parts)
        except Exception as e:
            self.log.debug("Could not handle GlusterFS version: %s", str(e))

    def parse_version(self, version):
        # type (str) -> str, str, str
        """
        GlusterFS versions are in format <major>.<minor>
        """
        major, minor, patch = None, None, None
        try:
            split_version = version.split('.')
            major, minor = split_version[0:2]
            if len(split_version) > 2:
                patch = split_version[2]
        except ValueError as e:
            self.log.debug("Unable to parse GlusterFS version %s: %s", str(version), str(e))
        return major, minor, patch

    def parse_volume_summary(self, output):
        for volume in output:
            volume_tags = ["vol_name:{}".format(volume.get('name')), "vol_type:{}".format(volume.get('type'))]
            volume_tags.extend(self._tags)
            self.submit_metrics(volume, 'volume', VOLUME_STATS, volume_tags)

            if 'subvols' in volume:
                self.parse_subvols_stats(volume.get('subvols', []), volume_tags)

            self.submit_service_check(self.VOLUME_SC, volume.get('health'), volume_tags)

    def parse_subvols_stats(self, subvols, volume_tags):
        for subvol in subvols:
            subvol_tags = volume_tags + ['subvol_name:{}'.format(subvol.get('name'))]
            self.submit_metrics(subvol, 'subvol', VOL_SUBVOL_STATS, subvol_tags)
            self.submit_service_check(self.BRICK_SC, subvol['health'], subvol_tags)

            for brick in subvol.get('bricks', []):
                brick_name = brick['name'].split(":")
                brick_server = brick_name[0]
                brick_export = brick_name[1]
                brick_type = brick['type']
                brick_device = brick['device']
                fs_name = brick['fs_name']
                tags = [
                    'brick_server:{}'.format(brick_server),
                    'brick_export:{}'.format(brick_export),
                    'type:{}'.format(brick_type),
                    'device:{}'.format(brick_device),
                    'fs_name:{}'.format(fs_name),
                ]
                tags.extend(subvol_tags)
                self.submit_metrics(brick, 'brick', BRICK_STATS, tags)

    def submit_metrics(self, payload, prefix, metric_mapping, tags):
        """
        Parse a payload with a given metric_mapping and submit metric for valid values.
        Some values contain measurements like `GiB` which should be removed and only submitted if consistent
        """
        for key, metric in metric_mapping.items():
            if key in payload:
                value = payload[key]

                if key in PARSE_METRICS:
                    try:
                        value_parsed = value.split(" ")
                        value = float(value_parsed[0])
                    except ValueError as e:
                        self.log.debug("Unable to parse value for %s: %s", key, str(e))
                        continue
                self.gauge('{}.'.format(prefix) + metric, value, tags)
            else:
                self.log.debug("Field not found in %s data: %s", prefix, key)

    def submit_service_check(self, sc_name, val, tags):
        msg = "Health in state: %s" % val
        status = val.lower()
        if status == 'up':
            self.service_check(sc_name, AgentCheck.OK, tags=tags)
        elif status == 'partial':
            self.service_check(sc_name, AgentCheck.WARNING, tags=tags, message=msg)
        elif status == 'degraded' or status == 'down':
            self.service_check(sc_name, AgentCheck.CRITICAL, tags=tags, message=msg)
        else:
            self.service_check(sc_name, AgentCheck.UNKNOWN, tags=tags, message=msg)

    def get_gstatus_data(self):
        options = type('', (), {})()
        options.volumes = False
        options.alldata = True
        options.brickinfo = False
        options.displayquota = False
        options.displaysnap = False
        options.units = "g"
        options.output_mode = "json"

        cluster = Cluster(options, self.log, self.use_sudo)
        # check_version(cluster)
        cluster.gather_data()

        return self.return_json(cluster)

    def return_json(self, data):
        from datetime import datetime

        # Build the cluster data for json
        gstatus = {}
        gstatus['cluster_status'] = data.cluster_status
        gstatus['glfs_version'] = data.glusterfs_version
        gstatus['node_count'] = data.nodes
        gstatus['nodes_active'] = data.nodes_reachable
        gstatus['volume_count'] = data.volume_count
        gstatus['volumes_started'] = data.volumes_started
        if data.volume_count:
            gstatus['volume_summary'] = data.volume_data

        return json.dumps({"last_updated": str(datetime.now()), "data": gstatus})
