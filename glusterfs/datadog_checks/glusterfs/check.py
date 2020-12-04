# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from typing import Any

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.config import _is_affirmative
from datadog_checks.base.utils.subprocess_output import get_subprocess_output

CLUSTER_STATS = {
    'node_count': 'nodes.count',
    'nodes_active': 'nodes.active',
    'volumes_started': 'volumes.started',
    'volume_count': 'volumes.count',
}


GENERAL_STATS = {
    'size_used': 'size.used',
    'inodes_free': 'inodes.free',
    'size_free': 'size.free',
    'size_total': 'size.total',
    'inodes_used': 'inodes.used',
    'inodes_total': 'inodes.total',
    'online': 'online',
}

VOL_SUBVOL_STATS = {
    'disperse': 'disperse',
    'disperse_redundancy': 'disperse_redundancy',
    'replica': 'replica',
}

VOLUME_STATS = {
    'v_used_percent': 'used.percent',
    'num_bricks': 'bricks.count',
    'distribute': 'distribute',
    'v_size_used': 'size.used',
    'v_size': 'size.total',
    'snapshot_count': 'snapshot.count',
}

VOLUME_STATS.update(GENERAL_STATS)
VOLUME_STATS.update(VOL_SUBVOL_STATS)

BRICK_STATS = {'block_size': 'block_size'}
BRICK_STATS.update(GENERAL_STATS)

PARSE_METRICS = ['v_size_used', 'v_size']

GLUSTER_VERSION = 'glfs_version'
CLUSTER_STATUS = 'cluster_status'

GSTATUS_PATH = '/opt/datadog-agent/embedded/sbin/gstatus'
INSTALL_PATH = '/usr/local/bin/gstatus'


class GlusterfsCheck(AgentCheck):
    __NAMESPACE__ = 'glusterfs'

    CLUSTER_SC = "cluster.health"
    VOLUME_SC = "volume.health"
    BRICK_SC = "brick.health"

    def __init__(self, name, init_config, instances):
        # type: (*Any, **Any) -> None
        super(GlusterfsCheck, self).__init__(name, init_config, instances)
        self._tags = self.instance.get('tags', [])

        # Check if customer set gstatus path
        if init_config.get('gstatus_path'):
            self.gstatus_cmd = init_config.get('gstatus_path')
        else:
            if os.path.exists(GSTATUS_PATH):
                self.gstatus_cmd = GSTATUS_PATH
            elif os.path.exists(INSTALL_PATH):
                self.gstatus_cmd = INSTALL_PATH
            else:
                raise ConfigurationError(
                    'Glusterfs check requires `gstatus` to be installed or set the path to the installed version.'
                )
        self.log.debug("Using gstatus path `%s`", self.gstatus_cmd)

    def check(self, _):
        use_sudo = _is_affirmative(self.instance.get('use_sudo', False))
        if use_sudo:
            test_sudo = os.system('setsid sudo -l < /dev/null')
            if test_sudo != 0:
                raise Exception('The dd-agent user does not have sudo access')
            gluster_args = ['sudo', self.gstatus_cmd]
        else:
            gluster_args = [self.gstatus_cmd]

        # Ensures units are universally the same by specifying the --units flag
        gluster_args += ['-a', '-o', 'json', '-u', 'g']
        self.log.debug("gstatus command: %s", gluster_args)
        output, _, _ = get_subprocess_output(gluster_args, self.log)
        gstatus = json.loads(output)

        if 'data' in gstatus:
            data = gstatus['data']
            self.submit_metric(data, 'cluster', CLUSTER_STATS, self._tags)

            self.submit_version_metadata(data)

            if 'volume_summary' in output:
                self.parse_volume_summary(data['volume_summary'])

            if CLUSTER_STATUS in data:
                status = data[CLUSTER_STATUS]
                if status == 'Healthy':
                    self.service_check(self.CLUSTER_SC, AgentCheck.OK, tags=self._tags)
                else:
                    self.service_check(
                        self.CLUSTER_SC, AgentCheck.CRITICAL, tags=self._tags, message="Cluster status is %s" % status
                    )
        else:
            self.log.warning("No data from gstatus")

    @AgentCheck.metadata_entrypoint
    def submit_version_metadata(self, data):
        try:
            raw_version = data[GLUSTER_VERSION]
        except KeyError as e:
            self.log.debug("Could not retrieve GlusterFS version: %s", str(e))

        if raw_version:
            version_parts = self.parse_version(raw_version)

            self.set_metadata('version', raw_version, scheme='parts', part_map=version_parts)
            self.log.debug('Found GlusterFS version: %s', raw_version)
        else:
            self.log.warning('Could not retrieve GlusterFS version info: %s', raw_version)

    def parse_version(self, version):
        """
        GlusterFS versions are in format <major>.<minor>
        """
        major, minor = version.split('.')

        return {
            'major': str(int(major)),
            'minor': str(int(minor))
        }

    def parse_volume_summary(self, output):
        for volume in output:
            volume_tags = ["vol_name:{}".format(volume['name']), "vol_type:{}".format(volume['type'])]
            volume_tags.extend(self._tags)
            self.submit_metric(volume, 'volume', VOLUME_STATS, volume_tags)

            if 'subvols' in volume:
                self.parse_subvols_stats(volume['subvols'], volume_tags)

            self.submit_service_check(self.VOLUME_SC, volume['health'], volume_tags)

    def parse_subvols_stats(self, subvols, volume_tags):
        for subvol in subvols:
            self.submit_metric(subvol, 'subvol', VOL_SUBVOL_STATS, volume_tags)

            if 'bricks' in subvol:
                for brick in subvol['bricks']:
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
                    tags.extend(self._tags)
                    self.submit_metric(brick, 'brick', BRICK_STATS, tags)

            self.submit_service_check(self.BRICK_SC, subvol['health'], tags)

    def submit_metric(self, payload, prefix, metric_mapping, tags):
        """
        Parse a payload with a given metric_mapping and submit metric for valid values.
        Some values contain measurements like `GiB` which should be removed and only submitted if consistent
        """
        for key, metric in metric_mapping.items():
            if key in payload:
                value = payload[key]

                if key in PARSE_METRICS:
                    value_parsed = value.split(" ")
                    if value_parsed[1] == "GiB":
                        value = value_parsed[0]
                    else:
                        self.log.debug("Measurement is not in GiB: %s", value)
                        continue
                self.gauge('{}.'.format(prefix) + metric, value, tags)
            else:
                self.log.debug("Field not found in %s data: %s", prefix, key)

    def submit_service_check(self, sc_name, status, tags):
        msg = "Health in state: %s" % status
        if status == 'up':
            self.service_check(sc_name, AgentCheck.OK, tags=tags)
        elif status == 'partial':
            self.service_check(sc_name, AgentCheck.WARNING, tags=tags, message=msg)
        else:
            self.submit_service_check(sc_name, AgentCheck.CRITICAL, tags=tags, message=msg)
