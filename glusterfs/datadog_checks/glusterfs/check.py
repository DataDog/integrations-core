# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from typing import Any
import os

from datadog_checks.base import AgentCheck
from datadog_checks.base.config import _is_affirmative
from datadog_checks.base.utils.subprocess_output import get_subprocess_output

CLUSTER_STATS = {
    'node_count': 'nodes.count',
    'nodes_active': 'nodes.active',
    'volumes_started': 'volumes.started',
    'volume_count': 'volumes.count'
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
#    'v_size_used': 'size.used', # strip GiB from value
#    'v_size': 'size.total', # strip GiB from value
    'snapshot_count': 'snapshot.count',
}
VOLUME_STATS.update(GENERAL_STATS)
VOLUME_STATS.update(VOL_SUBVOL_STATS)

BRICK_STATS = {
    'block_size': 'block_size'
}
BRICK_STATS.update(GENERAL_STATS)


GLUSTER_VERSION = 'glfs_version'
CLUSTER_STATUS = 'cluster_status'

class GlusterfsCheck(AgentCheck):
    __NAMESPACE__ = 'glusterfs'

    def __init__(self, *args, **kwargs):
        # type: (*Any, **Any) -> None
        super(GlusterfsCheck, self).__init__(*args, **kwargs)
        self._tags = self.instance.get('tags', [])

    def check(self, _):
        gstatus_cmd = 'gstatus'
        use_sudo = _is_affirmative(self.instance.get('use_sudo', False))
        if use_sudo:
            test_sudo = os.system('setsid sudo -l < /dev/null')
            if test_sudo != 0:
                raise Exception('The dd-agent user does not have sudo access')
            gluster_args = ['sudo', gstatus_cmd]
        else:
            gluster_args = [gstatus_cmd]

        gluster_args += ['-a', '-o', 'json']
        output, _, _ = get_subprocess_output(gluster_args, self.log)
        gstatus = json.loads(output)
        if 'data' in gstatus:
            data = gstatus['data']
            self.submit_metric(data, 'cluster', CLUSTER_STATS, self._tags)

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
            self.submit_metric(volume, 'volume', VOLUME_STATS, volume_tags)

            if 'subvols' in volume:
                self.parse_subvols_stats(volume['subvols'], volume_tags)

    def parse_subvols_stats(self, subvols, volume_tags):
        for subvol in subvols:
            self.submit_metric(subvol, 'subvol', VOL_SUBVOL_STATS, volume_tags)

            if 'bricks' in subvol:
                for brick in subvol['bricks']:
                    # brick_name:172.29.187.90:/export/xvdf1/brick
                    # split this tag into server + export tags
                    brick_name = brick['name']
                    brick_type = brick['type']
                    brick_device = brick['device']
                    fs_name = brick['fs_name']
                    tags = ['brick_name:{}'.format(brick_name),
                            'type:{}'.format(brick_type),
                            'device:{}'.format(brick_device),
                            'fs_name:{}'.format(fs_name)]
                    tags.extend(self._tags)
                    self.submit_metric(brick, 'brick', BRICK_STATS, tags)

    def submit_metric(self, payload, prefix, metric_mapping, tags):
        for key, metric in metric_mapping.items():
            if key in payload:
                self.gauge('{}.'.format(prefix) + metric, payload[key], tags)
            else:
                self.log.debug("Field not found in %s data: %s", prefix, key)
