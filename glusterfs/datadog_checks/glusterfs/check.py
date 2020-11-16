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

VOLUME_STATS = {
    'v_used_percent': 'used.percent',
    'num_bricks': 'bricks.count',
    'distribute': 'distribute',
    'v_size_used': 'size.used', # strip GiB from value
    'v_size': 'size.total', # strip GiB from value
    'snapshot_count': 'snapshot.count',
}

VOL_SUBVOL_STATS = {
    'disperse': 'disperse',
    'disperse_redundancy': 'disperse_redundancy',
    'replica': 'replica',
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
        output, _, _ = get_subprocess_output(['gstatus', '-a', '-o', 'json'], self.log)
        gstatus = json.loads(output)
        if 'data' in gstatus:
            data = gstatus['data']
            for key, metric in CLUSTER_STATS.items():
                if key in data:
                    self.gauge(metric, data[key], self._tags)

            if 'volume_summary' in output:
                self.parse_volume_summary(data['volume_summary'])
        else:
            self.log.warning("No data from gstatus")

    def parse_volume_summary(self, output):
        for volume in output:
            volume_tags = ["vol_name:{}".format(volume['name']), "vol_type:{}".format(volume['type'])]
            volume_tags.extend(self._tags)
            for key, metric in VOLUME_STATS.items():
                if key in volume:
                    self.gauge(metric, volume[key], volume_tags)
                else:
                    self.log.debug("Field not found in volume data: %s", key)


