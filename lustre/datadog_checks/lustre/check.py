# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any  # noqa: F401

from datadog_checks.base import AgentCheck  # noqa: F401
import subprocess
import yaml
from dataclasses import dataclass

OSS_JOBSTATS_PARAM_REGEX = 'ost.*.job_stats'
MDS_JOBSTATS_PARAM_REGEX = 'obdfilter.*.job_stats'

IGNORED_STATS = {
    'snapshot_time',
    'start_time',
    'elapsed_time',
}

@dataclass
class LustreParam:
    regex: str
    node_types: tuple[str, ...]
    wildcards: tuple[str, ...] = ()
    prefix: str = ''

DEFAULT_PARAMS = [
    LustreParam(regex='llite.*.stats', node_types=('client',), wildcards=('component_uuid',), prefix='filesystem'),
]

EXTRA_PARAMS = [
    LustreParam(regex='mds.MDS.mdt.stats', node_types=('mds',), prefix='mds.mdt'),
    LustreParam(regex='mdt.*.exports.*.stats', node_types=('mds',), wildcards=('component_name','nid'), prefix='mds.mdt.exports'),
    LustreParam(regex='mdc.*.stats', node_types=('client',), wildcards=('component_uuid',), prefix='mdc'),
    LustreParam(regex='ldlm.services.*.stats', node_types=('client', 'mds', 'oss'), wildcards=('ldlm_service',), prefix='ldlm.services'),
    LustreParam(regex='ldlm.namespaces.*.pool.stats', node_types=('client', 'mds', 'oss'), wildcards=('component_uuid',), prefix='ldlm.namespaces.pool'),
    LustreParam(regex='mgs.MGS.exports.*.stats', node_types=('mds',), wildcards=('component_name', 'nid'), prefix='mgs.exports'),
    LustreParam(regex='ost.OSS.oss.stats', node_types=('oss',), prefix='ost.oss'),
    LustreParam(regex='osc.*.stats', node_types=('client',), wildcards=('component_uuid',), prefix='osc'),
    LustreParam(regex='obdfilter.*.exports.*.stats', node_types=('oss',), wildcards=('component_name', 'nid'), prefix='obdfilter.exports'),
    LustreParam(regex='obdfilter.*.stats', node_types=('oss',), wildcards=('component_name',), prefix='obdfilter'),
]

class LustreCheck(AgentCheck):

    __NAMESPACE__ = 'lustre'

    def __init__(self, name, init_config, instances):
        super(LustreCheck, self).__init__(name, init_config, instances)

        self.filesystems = self.instance.get("filesystems", [])
        self.lctl_path = self.instance.get("lctl_path", "/usr/sbin/lctl")
        self.lnetctl_path = self.instance.get("lnetctl_path", "/usr/sbin/lnetctl")
        self.lnetctl_detailed = self.instance.get("enable_lnetctl_detailed", False)
        self.lnetctl_health = self.instance.get("enable_lnetctl_health", False)
        self.node_type = self.instance.get("node_type", self.get_node_type())

        self.param_list = DEFAULT_PARAMS
        if self.instance.get("enable_extra_params", False):
            self.param_list += EXTRA_PARAMS



    def check(self, _):
        self.submit_jobstats_metrics()
        # self.submit_lnet_metrics()
        # self.submit_lnet_local_ni_metrics()
        # self.submit_lnet_peer_ni_metrics()

    def get_node_type(self):
        '''
        Determine the host type from the command line.
        '''
        self.log.debug('Determining node type...')
        cmd = f'{self.lctl_path} dl'
        try:
            output_lines = subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.splitlines()
            # Example line:   0 UP osd-ldiskfs lustre-OST0001-osd lustre-OST0001-osd_UUID 5
            devices = [line.strip().split()[2] for line in output_lines]
            if 'mdt' in devices:
                return 'mds'
            elif 'ost' in devices:
                return 'oss'
            else:
                return 'client'
        except Exception as e:
            self.log.error(f'Failed to determine node type: {e}')
            return 'client'

    # TODO: add timeouts to subprocess calls
    # TODO: confider abstracting to lctl.run() method
    # TODO: same for lnet
    def lctl_list_param(self, param_regex):
        '''
        List the parameters from the command line.
        '''
        cmd = f'{self.lctl_path} list_param {param_regex}'
        try:
            return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.splitlines()
        except Exception as e:
            self.log.error(f'Failed to list parameters for {param_regex}: {e}')
            return []

    def lctl_get_param(self, param_regex):
        '''
        Get the value of a parameter from the command line.
        '''
        cmd = f'{self.lctl_path} get_param -ny {param_regex}'
        try:
            return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout
        except Exception as e:
            self.log.error(f'Failed to get data for {param_regex}: {e}')
            return ''

    def lnet_get_stats(self, stats_type):
        '''
        Show the lnet stats from the command line.
        '''
        cmd = f'sudo {self.lnetctl_path} {stats_type} show -v 3'
        try:
            return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout
        except Exception as e:
            self.log.error(f'Failed to show lnet stats: {e}')
            return ''

    def submit_jobstats_metrics(self):
        '''
        Submit the jobstats metrics to Datadog.
        '''
        jobstats_params = self.get_jobstats_params_list(self.node_type)
        for jobstats_param in jobstats_params:
            component_name = jobstats_param.split('.')[1]  # For example: lustre-MDT0000
            if self.filesystems and not any(component_name.startswith(filesystem) for filesystem in self.filesystems):
                continue
            jobstats_metrics = self.get_jobstats_metrics(jobstats_param)['job_stats']
            for job in jobstats_metrics:
                job_id = job['job_id']
                for metric_name, metric_values in job.items():
                    if not isinstance(metric_values, dict):
                        continue
                    for metric_type, metric_value in metric_values.items():
                        if metric_type == 'unit':
                            continue
                        if metric_type == 'hist':
                            # TODO: Handle histogram metrics if needed
                            continue 
                        self.log.warning(f'Jobstats metric {metric_name} with type {metric_type} has value {metric_value}')
                        self.gauge(f'job_stats.{metric_name}.{metric_type}', metric_value, tags=[f'component_type:{self.node_type}', f'component_name:{component_name}', f'job_id:{job_id}'])


    def get_jobstats_params_list(self, component_type):
        '''
        Get the jobstats params from the command line.
        '''
        if component_type.lower() == 'mds':
            param_regex = MDS_JOBSTATS_PARAM_REGEX
        elif component_type.lower() == 'oss':
            param_regex = OSS_JOBSTATS_PARAM_REGEX
        elif component_type.lower() == 'client':
            self.log.debug(f'Client component_type has no jobstats parameters.')
            return []
        else:
            self.log.debug(f'Invalid component_type: {component_type}')
            return []
        return self.lctl_list_param(param_regex)


    def get_jobstats_metrics(self, jobstats_param):
        '''
        Get the jobstats metrics for a given jobstats param.
        '''
        jobstats_output = self.lctl_get_param(jobstats_param)
        try:
            return yaml.safe_load(jobstats_output)
        except KeyError:
            self.log.debug(f'No jobstats metrics found for {jobstats_param}')
            return {}
    
    def submit_lnet_stats_metrics(self):
        '''
        Submit the lnet metrics.
        '''
        lnet_metrics = self.get_lnet_metrics('stats')['statistics']
        for metric in lnet_metrics:
            self.gauge(f'net.{metric}', lnet_metrics[metric], tags=[f'node_type:{self.node_type}'])

    def get_lnet_metrics(self, stats_type='stats'):
        '''
        Get the lnet stats from the command line.
        '''
        lnet_stats = self.lnet_get_stats(stats_type)
        try:
            return yaml.safe_load(lnet_stats)
        except (KeyError, ValueError):
            self.log.debug(f'No lnet stats found')
            return {}
    
    def submit_lnet_local_ni_metrics(self):
        '''
        Submit the lnet local ni metrics.
        '''
        lnet_local_stats = self.get_lnet_metrics('net')['net']
        for net in lnet_local_stats:
            net_type = net.get('net type')
            for ni in net.get('local NI(s)', []):
                nid = ni.get('nid')
                tags = [f'net_type:{net_type}', f'nid:{nid}']
                for stats_group_name, stats_group in ni.items():
                    if not isinstance(stats_group, dict):
                        continue
                    for metric_name, metric_value in stats_group.items():
                        if isinstance(metric_value, int):
                            self.gauge(f'net.local.{stats_group_name.replace(" ", "_")}.{metric_name.replace(" ", "_")}', metric_value, tags=tags)

    def submit_lnet_peer_ni_metrics(self):
        '''
        Submit the lnet peer ni metrics.
        '''
        lnet_peer_stats = self.get_lnet_metrics('peer')['peer']
        for peer in lnet_peer_stats:
            nid = peer.get('primary nid')
            for ni in peer.get('peer ni', []):
                peer_nid = ni.get('nid')
                tags = [f'nid:{nid}', f'peer_nid:{peer_nid}']
                for stats_group_name, stats_group in ni.items():
                    if not isinstance(stats_group, dict):
                        continue
                    for metric_name, metric_value in stats_group.items():
                        if isinstance(metric_value, int):
                            self.gauge(f'net.peer.{stats_group_name.replace(" ", "_")}.{metric_name.replace(" ", "_")}', metric_value, tags=tags)

    def submit_general_stats(self):
        '''
        Submit general stats.
        '''
        for param in self.param_list: 
            if not param.regex.endswith('.stats'):
                continue
            raw_stats = self.lctl_get_param(param.regex)
            parsed_stats = self.parse_stats(raw_stats)
            for stat_name, stat_value in parsed_stats.items():
                if isinstance(stat_value, int):
                    self.gauge(f'general.{stat_name}', stat_value, tags=[f'node_type:{self.node_type}'])
                    continue
                if not isinstance(stat_value, dict):
                    self.log.debug(f'Unexpected stat value for {stat_name}: {stat_value}')
                    continue
                for metric_type, metric_value in stat_value.items():
                    if isinstance(metric_value, int):
                        self.gauge(f'general.{stat_name}.{metric_type}', metric_value, tags=[f'node_type:{self.node_type}'])
                    else:
                        self.log.debug(f'Unexpected metric value for {stat_name}.{metric_type}: {metric_value}')


    def parse_stats(self, raw_stats):
        '''
        Parse the raw stats into a dictionary.
        '''
        stats = {}
        for line in raw_stats.splitlines():
            # elapsed_time              2068792.478877751 secs.nsecs
            # req_waittime              83 samples [usecs] 11 40 1493 32135
            # req_qdepth                83 samples [reqs] 0 0 0 0
            # cancel                    253 samples [locks] 1 1 253
            # tgtreg                    2 samples [reqs]
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            stat_name = parts[0]
            if stat_name in IGNORED_STATS:
                continue
            try:
                stat_value = {"count": int(parts[1]), "unit": parts[3].strip('[]')}
                stat_types = ('min', 'max', 'sum', 'sumsq')
                for i, value in enumerate(parts[4:]):
                    stat_value[stat_types[i]] = int(value)
                if len(parts) > 8:
                    self.log.debug(f'Unexpected format for stat "{line}"')
            except ValueError:
                self.log.debug(f'Could not parse stat value for "{line}"')
                continue
            stats[stat_name] = stat_value
        return stats
