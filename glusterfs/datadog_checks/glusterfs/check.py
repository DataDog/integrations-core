# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from typing import Any

from six import iteritems

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.config import is_affirmative
from datadog_checks.base.utils.subprocess_output import get_subprocess_output

from .metrics import BRICK_STATS, CLUSTER_STATS, PARSE_METRICS, VOL_SUBVOL_STATS, VOLUME_STATS

GLUSTER_VERSION = 'glfs_version'
CLUSTER_STATUS = 'cluster_status'

GSTATUS_PATH = '/opt/datadog-agent/embedded/sbin/gstatus'


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
            else:
                raise ConfigurationError(
                    'Glusterfs check requires `gstatus` to be installed or set the path to the installed version.'
                )
        self.log.debug("Using gstatus path `%s`", self.gstatus_cmd)

    def check(self, _):
        use_sudo = is_affirmative(self.instance.get('use_sudo', False))
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
        try:
            gstatus = json.loads(output)
        except json.JSONDecoderError as e:
            self.log.debug("Unable to decode gstatus output: %s", str(e))
            raise

        if 'data' in gstatus:
            data = gstatus['data']
            self.submit_metrics(data, 'cluster', CLUSTER_STATS, self._tags)

            self.submit_version_metadata(data)

            if 'volume_summary' in output:
                self.parse_volume_summary(data['volume_summary'])

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
        try:
            major, minor = version.split('.')
        except ValueError as e:
            self.log.debug("Unable to parse GlusterFS version: %s", str(e))
        else:
            return {'major': str(int(major)), 'minor': str(int(minor))}

    def parse_volume_summary(self, output):
        for volume in output:
            volume_tags = ["vol_name:{}".format(volume['name']), "vol_type:{}".format(volume['type'])]
            volume_tags.extend(self._tags)
            self.submit_metrics(volume, 'volume', VOLUME_STATS, volume_tags)

            if 'subvols' in volume:
                self.parse_subvols_stats(volume['subvols'], volume)

            self.submit_service_check(self.VOLUME_SC, volume['health'], volume_tags)

    def parse_subvols_stats(self, subvols, volume_tags):
        for subvol in subvols:
            self.submit_metric(subvol, 'subvol', VOL_SUBVOL_STATS, volume_tags)

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
                tags.extend(self._tags)
                self.submit_metrics(brick, 'brick', BRICK_STATS, tags)

            self.submit_service_check(self.BRICK_SC, subvol['health'], volume_tags)

    def submit_metrics(self, payload, prefix, metric_mapping, tags):
        """
        Parse a payload with a given metric_mapping and submit metric for valid values.
        Some values contain measurements like `GiB` which should be removed and only submitted if consistent
        """
        for key, metric in iteritems(metric_mapping):
            if key in payload:
                value = payload[key]

                if key in PARSE_METRICS:
                    try:
                        value_parsed = value.split(" ")
                        value = int(value_parsed[0])
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
        else:
            # Degraded or Down
            self.service_check(sc_name, AgentCheck.CRITICAL, tags=tags, message=msg)
