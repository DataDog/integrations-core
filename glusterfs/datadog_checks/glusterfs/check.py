# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import subprocess
from typing import Any

from datadog_checks.base import AgentCheck
from datadog_checks.base.config import is_affirmative

from .gluster_xml import (
    GlusterXMLError,
    build_cluster_data,
    parse_gluster_version,
    parse_heal_info,
    parse_pool_list,
    parse_volume_info,
    parse_volume_status,
)
from .metrics import BRICK_STATS, CLUSTER_STATS, HEAL_INFO_STATS, VOL_SUBVOL_STATS, VOLUME_STATS

GLUSTER_VERSION = 'glfs_version'
CLUSTER_STATUS = 'cluster_status'

# Per-command timeout in seconds. A hung ``gluster`` command (for example
# ``volume heal <vol> info`` on a volume whose self-heal daemon is unresponsive)
# must not block the agent indefinitely.
GLUSTER_TIMEOUT = 30


class GlusterfsCheck(AgentCheck):
    __NAMESPACE__ = 'glusterfs'

    CLUSTER_SC = "cluster.health"
    VOLUME_SC = "volume.health"
    BRICK_SC = "brick.health"

    def __init__(self, name, init_config, instances):
        super(GlusterfsCheck, self).__init__(name, init_config, instances)
        self._tags = self.instance.get('tags', [])

        gluster_command = self.instance.get('gluster_command') or ['gluster']
        if isinstance(gluster_command, str):
            gluster_command = [gluster_command]
        self.gluster_command = list(gluster_command)

        self.use_sudo = is_affirmative(self.instance.get('use_sudo', True))

        # gstatus_path is no longer used; the check calls the ``gluster`` CLI
        # directly. Warn if a user is still setting it so they can clean up.
        if init_config.get('gstatus_path'):
            self.log.warning(
                "`gstatus_path` is no longer supported; the glusterfs check now calls the `gluster` "
                "CLI directly. Use the `gluster_command` instance option to point at a custom "
                "`gluster` path or wrapper."
            )

    def check(self, _):
        if self.use_sudo:
            self._verify_sudo()

        try:
            data = self._collect()
        except (GlusterXMLError, subprocess.CalledProcessError, FileNotFoundError) as e:
            self.log.warning("Encountered error trying to collect gluster status: %s", str(e))
            raise

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

    def _verify_sudo(self):
        # ``gluster`` requires root for status collection. Confirm the dd-agent
        # user has passwordless sudo for it before relying on it in check().
        cmd = ['sudo', '-ln', *self.gluster_command]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 or not result.stdout:
            raise Exception('The dd-agent user does not have sudo access: {!r}'.format(result.stderr or result.stdout))

    def _run_gluster(self, *args: str, xml: bool = True) -> str:
        cmd = ['sudo'] if self.use_sudo else []
        cmd += self.gluster_command
        if xml:
            cmd += ['--xml', '--mode=script']
        cmd += list(args)
        self.log.debug("gluster command: %s", ' '.join(cmd))
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=GLUSTER_TIMEOUT)
        except subprocess.TimeoutExpired as e:
            raise GlusterXMLError(f"gluster command timed out after {GLUSTER_TIMEOUT}s: {' '.join(cmd)}") from e
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, ' '.join(cmd), output=result.stdout, stderr=result.stderr
            )
        return result.stdout

    def _collect(self) -> dict[str, Any]:
        volume_info_xml = self._run_gluster('volume', 'info')
        volume_status_xml = self._run_gluster('volume', 'status', 'all', 'detail')
        pool_list_xml = self._run_gluster('pool', 'list')
        version_text = self._run_gluster('--version', xml=False)

        volumes = parse_volume_info(volume_info_xml)
        volumes = parse_volume_status(volume_status_xml, volumes)

        for vol in volumes:
            # Self-heal info is supplementary: the self-heal daemon may be
            # unresponsive or the volume stopped, in which case ``volume heal``
            # can fail or hang. Collect it best-effort so a heal failure never
            # suppresses the cluster/volume/brick metrics collected above.
            vol['healinfo'] = []
            if vol['status'].lower() == 'started':
                try:
                    heal_xml = self._run_gluster('volume', 'heal', vol['name'], 'info')
                    vol['healinfo'] = parse_heal_info(heal_xml)
                except (GlusterXMLError, subprocess.CalledProcessError) as e:
                    self.log.warning("Unable to get self-heal status for volume %s: %s", vol['name'], e)

        peers = parse_pool_list(pool_list_xml)
        glusterfs_version = parse_gluster_version(version_text)
        return build_cluster_data(volumes, peers, glusterfs_version)

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

            if 'healinfo' in volume:
                self.parse_healinfo_stats(volume.get('healinfo', []), volume_tags)

            if 'health' in volume:
                self.submit_service_check(self.VOLUME_SC, volume['health'], volume_tags)

    def parse_subvols_stats(self, subvols, volume_tags):
        for subvol in subvols:
            subvol_tags = volume_tags + ['subvol_name:{}'.format(subvol.get('name'))]
            self.submit_metrics(subvol, 'subvol', VOL_SUBVOL_STATS, subvol_tags)

            if 'health' in subvol:
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

    def parse_healinfo_stats(self, healinfo, volume_tags):
        for info in healinfo:
            if info['status'].lower() != 'connected':
                continue

            brick_name = info['name'].split(":")
            brick_server = brick_name[0]
            brick_export = brick_name[1]
            tags = [
                'brick_server:{}'.format(brick_server),
                'brick_export:{}'.format(brick_export),
            ]
            tags.extend(volume_tags)
            self.submit_metrics(info, 'heal_info', HEAL_INFO_STATS, tags)

    def submit_metrics(self, payload, prefix, metric_mapping, tags):
        """
        Parse a payload with a given metric_mapping and submit metric for valid values.
        """
        for key, metric in metric_mapping.items():
            if key in payload:
                value = payload[key]

                if isinstance(value, str) and value.lower() == 'n/a':
                    continue

                self.gauge('{}.{}'.format(prefix, metric), value, tags)
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
