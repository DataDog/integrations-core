# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any  # noqa: F401

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.lustre.common import LCTL_PATH, IGNORED_JOBSTATS_METRICS, MDS_JOBSTATS_PARAM_REGEX, OSS_JOBSTATS_PARAM_REGEX
import subprocess
import yaml

    
class LustreCheck(AgentCheck):

    __NAMESPACE__ = 'lustre'

    def __init__(self, name, init_config, instances):
        super(LustreCheck, self).__init__(name, init_config, instances)

        self.filesystems = self.instance.get("filesystems", [])
        self.node_type = self.instance.get("node_type", self.get_node_type())
        self.lctl_path = self.instance.get("lctl_path", "/usr/sbin/lctl")
        self.lnetctl_path = self.instance.get("lnetctl_path", "/usr/sbin/lnetctl")


    def check(self, _):
        self.submit_jobstats_metrics(self.node_type)

    def get_node_type(self):
        '''
        Determine the host type from the command line.
        '''

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

    def lctl_get_param(self, param):
        '''
        Get the value of a parameter from the command line.
        '''
        cmd = f'{self.lctl_path} get_param -ny {param}'
        try:
            return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout
        except Exception as e:
            self.log.error(f'Failed to get data for {param}: {e}')
            return ''

    def submit_jobstats_metrics(self, component_type):
        '''
        Submit the jobstats metrics to Datadog.
        '''
        jobstats_params = self.get_jobstats_params_list(component_type)
        for jobstats_param in jobstats_params:
            component_name = jobstats_param.split('.')[1]
            if self.filesystems and not any(component_name.startswith(filesystem) for filesystem in self.filesystems):
                continue
            jobstats_metrics = self.get_jobstats_metrics(jobstats_param)
            for job in jobstats_metrics:
                job_id = job['job_id']
                for metric_name, metric_values in job.items():
                    if metric_name in IGNORED_JOBSTATS_METRICS:
                        continue
                    for metric_type, metric_value in metric_values.items():
                        self.gauge(f'lustre.jobstats.{metric_name}.{metric_type}', metric_value, tags=[f'component_type:{component_type}', f'component_name:{component_name}', f'job_id:{job_id}'])


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
            return yaml.safe_load(jobstats_output)['job_stats']
        except KeyError:
            self.log.debug(f'No jobstats metrics found for {jobstats_param}')
            return []
    
    def submit_lnet_metrics(self):
        '''
        Submit the lnet metrics to Datadog.
        '''
        lnet_stats = self.get_lnet_stats()
        for lnet_stat in lnet_stats:
            self.gauge(f'lustre.net.{lnet_stat}', lnet_stats[lnet_stat], tags=[f'node_type:{self.node_type}'])

    def get_lnet_stats(self):
        '''
        Get the lnet stats from the command line.
        '''
        cmd = f'sudo {self.lnetctl_path} stats show'
        lnet_stats = subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout
        try:
            return yaml.safe_load(lnet_stats)['statistics']
        except ValueError:
            self.log.debug(f'No lnet stats found')
            return ''
    