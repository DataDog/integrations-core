# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from typing import Any

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.subprocess_output import get_subprocess_output

CLUSTER_STATS = {
    'node_count': 'cluster.nodes.count',
    'nodes_active': 'cluster.nodes.active',
    'volumes_started': 'cluster.volumes.started',
    'volume_count': 'cluster.volumes.count'
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

VOLUME_STATS = {
    'v_used_percent': 'used.percent',
    'num_bricks': 'bricks.count',
    'distribute': 'distribute',
#    'v_size_used': 'size.used', # strip GiB from value
#    'v_size': 'size.total', # strip GiB from value
    'snapshot_count': 'snapshot.count',
}

VOL_SUBVOL_STATS = {
    'disperse': 'disperse',
    'disperse_redundancy': 'disperse_redundancy',
    'replica': 'replica',
}

BRICK_STATS = {
    'block_size': 'block_size'
}


GLUSTER_VERSION = 'glfs_version'
CLUSTER_STATUS = 'cluster_status'

class GlusterfsCheck(AgentCheck):
    __NAMESPACE__ = 'glusterfs'

    def __init__(self, *args, **kwargs):
        # type: (*Any, **Any) -> None
        super(GlusterfsCheck, self).__init__(*args, **kwargs)
        self._tags = self.instance.get('tags', [])

    def check(self, _):
        output, _, _ = get_subprocess_output(['gstatus', '-a', '-o', 'json'], self.log)
        gstatus = json.loads(output)
        if 'data' in gstatus:
            data = gstatus['data']
            for key, metric in CLUSTER_STATS.items():
                if key in data:
                    self.gauge(metric, data[key], self._tags)
            self.submit_version_metadata(data)

            if 'volume_summary' in output:
                self.parse_volume_summary(data['volume_summary'])
        else:
            self.log.warning("No data from gstatus")

    def submit_version_metadata(self, data):
        if GLUSTER_VERSION in data:
            version = data[GLUSTER_VERSION]
            self.set_metadata('version', version)

    def parse_volume_summary(self, output):
        for volume in output:
            volume_tags = ["vol_name:{}".format(volume['name']), "vol_type:{}".format(volume['type'])]
            volume_tags.extend(self._tags)
            unprefixed_metrics = {}
            unprefixed_metrics.update(GENERAL_STATS)
            unprefixed_metrics.update(VOL_SUBVOL_STATS)
            for key, metric in VOLUME_STATS.items():
                if key in volume:
                    self.gauge(metric, volume[key], volume_tags)
                else:
                    self.log.debug("Field not found in volume data: %s", key)
            for key, metric in unprefixed_metrics.items():
                if key in volume:
                    self.gauge('volume.' + metric, volume[key], volume_tags)
                else:
                    self.log.debug("Field not found in volume data: %s", key)
            if 'subvols' in volume:
                self.parse_subvols_stats(volume['subvols'], volume_tags)

    def parse_subvols_stats(self, subvols, volume_tags):
        for subvol in subvols:
            for key, metric in VOL_SUBVOL_STATS.items():
                if key in subvol:
                    self.gauge(metric, subvol[key], volume_tags)
                else:
                    self.log.debug("Field not found in subvol data: %s", key)

            if 'bricks' in subvol:
                for brick in subvol['bricks']:
                    brick_name = brick['name']
                    brick_type = brick['type']
                    brick_device = brick['device']
                    fs_name = brick['fs_name']
                    tags = ['brick_name:{}'.format(brick_name),
                            'type:{}'.format(brick_type),
                            'device:{}'.format(brick_device),
                            'fs_name:{}'.format(fs_name)]
                    tags.extend(self._tags)
                    for key, metric in BRICK_STATS.items():
                        if key in brick:
                            self.gauge(metric, brick[key], tags)
                        else:
                            self.log.debug("Field not found in brick data: %s", key)

                    for key, metric in GENERAL_STATS.items():
                        if key in brick:
                            self.gauge('brick.' + metric, brick[key], tags)
                        else:
                            self.log.debug("Field not found in brick data: %s", key)
