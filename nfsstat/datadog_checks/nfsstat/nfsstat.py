# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

from datadog_checks.checks import AgentCheck
from datadog_checks.utils.subprocess_output import get_subprocess_output

EVENT_TYPE = SOURCE_TYPE_NAME = 'nfsstat'


class NfsStatCheck(AgentCheck):

    metric_prefix = 'system.nfs.'

    def __init__(self, name, init_config, agentConfig, instances):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        # if they set the path, use that
        if init_config.get('nfsiostat_path'):
            self.nfs_cmd = [init_config.get('nfsiostat_path'), '1', '2']
        else:
            # if not, check if it's installed in the opt dir, if so use that
            if os.path.exists('/opt/datadog-agent/embedded/sbin/nfsiostat'):
                self.nfs_cmd = ['/opt/datadog-agent/embedded/sbin/nfsiostat', '1', '2']
            # if not, then check if it is in the default place
            elif os.path.exists('/usr/local/sbin/nfsiostat'):
                self.nfs_cmd = ['/usr/local/sbin/nfsiostat', '1', '2']
            else:
                raise Exception(
                    'nfsstat check requires nfsiostat be installed, please install it '
                    '(through nfs-utils) or set the path to the installed version'
                )

    def check(self, instance):
        stat_out, err, _ = get_subprocess_output(self.nfs_cmd, self.log)
        all_devices = []
        this_device = []
        custom_tags = instance.get("tags", [])

        for l in stat_out.splitlines():
            if not l:
                continue
            elif l.find('mounted on') >= 0 and len(this_device) > 0:
                # if it's a new device, create the device and add it to the array
                device = Device(this_device, self.log)
                all_devices.append(device)
                this_device = []
            this_device.append(l.strip().split())

        # Add the last device into the array
        device = Device(this_device, self.log)
        all_devices.append(device)

        # Disregard the first half of device stats (report 1 of 2)
        # as that is the moving average
        all_devices = all_devices[len(all_devices) // 2:]

        for device in all_devices:
            device.send_metrics(self.gauge, custom_tags)


class Device(object):

    def __init__(self, device_data, log):
        self.log = log

        self._device_data = device_data
        self._parse_device_header()
        self._parse_tags()

        self._parse_ops()
        self._parse_read_data()
        self._parse_write_data()

    def _parse_device_header(self):
        self._device_header = self._device_data[0]
        self.log.info(self._device_header)
        self.device_name = self._device_header[0]
        self.mount = self._device_header[-1][:-1]
        self.nfs_server = self.device_name.split(':')[0]
        self.nfs_export = self.device_name.split(':')[1]

    def _parse_ops(self):
        ops = self._device_data[2]
        self.ops = float(ops[0])
        self.rpc_bklog = float(ops[1])

    def _parse_read_data(self):
        read_data = self._device_data[4]
        self.read_ops = float(read_data[0])
        self.read_kb_per_s = float(read_data[1])
        self.read_kb_per_op = float(read_data[2])
        self.read_retrans = float(read_data[3])
        self.read_retrans_pct = read_data[4].strip('(').strip(')').strip('%')
        self.read_retrans_pct = float(self.read_retrans_pct)
        self.read_avg_rtt = float(read_data[5])
        self.read_avg_exe = float(read_data[6])

    def _parse_write_data(self):
        write_data = self._device_data[6]
        self.write_ops = float(write_data[0])
        self.write_kb_per_s = float(write_data[1])
        self.write_kb_per_op = float(write_data[2])
        self.write_retrans = float(write_data[3])
        self.write_retrans_pct = write_data[4].strip('(').strip(')').strip('%')
        self.write_retrans_pct = float(self.write_retrans_pct)
        self.write_avg_rtt = float(write_data[5])
        self.write_avg_exe = float(write_data[6])

    def _parse_tags(self):
        self.tags = []
        self.tags.append('nfs_server:{0}'.format(self.nfs_server))
        self.tags.append('nfs_export:{0}'.format(self.nfs_export))
        self.tags.append('nfs_mount:{0}'.format(self.mount))

    def send_metrics(self, gauge, tags):
        metric_prefix = 'system.nfs.'
        self.tags.extend(tags)
        gauge(metric_prefix + 'ops', self.ops, tags=self.tags)
        gauge(metric_prefix + 'rpc_bklog', self.rpc_bklog, tags=self.tags)

        read_metric_prefix = metric_prefix + 'read'
        gauge(read_metric_prefix + '.ops', self.read_ops, tags=self.tags)
        gauge(read_metric_prefix + '_per_op', self.read_kb_per_op, tags=self.tags)
        gauge(read_metric_prefix + '_per_s', self.read_kb_per_s, tags=self.tags)
        gauge(read_metric_prefix + '.retrans', self.read_retrans, tags=self.tags)
        gauge(read_metric_prefix + '.retrans.pct', self.read_retrans_pct, tags=self.tags)
        gauge(read_metric_prefix + '.rtt', self.read_avg_rtt, tags=self.tags)
        gauge(read_metric_prefix + '.exe', self.read_avg_exe, tags=self.tags)

        write_metric_prefix = metric_prefix + 'write'
        gauge(write_metric_prefix + '.ops', self.write_ops, tags=self.tags)
        gauge(write_metric_prefix + '_per_op', self.write_kb_per_op, tags=self.tags)
        gauge(write_metric_prefix + '_per_s', self.write_kb_per_s, tags=self.tags)
        gauge(write_metric_prefix + '.retrans', self.write_retrans, tags=self.tags)
        gauge(write_metric_prefix + '.retrans.pct', self.write_retrans_pct, tags=self.tags)
        gauge(write_metric_prefix + '.rtt', self.write_avg_rtt, tags=self.tags)
        gauge(write_metric_prefix + '.exe', self.write_avg_exe, tags=self.tags)
