# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import re
import shlex

# project
from checks import AgentCheck
from utils.subprocess_output import get_subprocess_output
from collections import defaultdict

EVENT_TYPE = SOURCE_TYPE_NAME = 'cassandra_check'
DEFAULT_HOST = 'localhost'
DEFAULT_PORT = '7199'

class CassandraCheck(AgentCheck):

    datacenter_name_re = re.compile('^Datacenter: (.*)')
    host_status_re = re.compile('^(?P<status>[UD])[NLJM].* (?P<owns>(\d+\.\d+%)|\?).*')

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

    def check(self, instance):
        # Allow to specify a complete command for nodetool such as `docker exec container nodetool`
        nodetool_cmd = shlex.split(instance.get("nodetool", "/usr/bin/nodetool"))
        host = instance.get("host", DEFAULT_HOST)
        port = instance.get("port", DEFAULT_PORT)
        keyspaces = instance.get("keyspaces", [])
        username = instance.get("username", "")
        password = instance.get("password", "")
        tags = instance.get("tags", [])

        for keyspace in keyspaces:
            # Build the nodetool command
            cmd = nodetool_cmd + ['-h', host, '-p', port]
            if username and password:
                cmd += ['-u', username, '-pw', password]
            cmd += ['status', '--', keyspace]

            # Execute the command
            out, err, _ = get_subprocess_output(cmd, self.log, False)
            if err or 'Error:' in out:
                self.log.error('Error executing nodetool status: %s', err or out)
            percent_up_by_dc, percent_total_by_dc = self._process_nodetool_output(out)
            for datacenter, percent_up in percent_up_by_dc.items():
                self.gauge('cassandra.replication_availability', percent_up,
                           tags=tags + ['keyspace:%s' % keyspace, 'datacenter:%s' % datacenter])
            for datacenter, percent_total in percent_total_by_dc.items():
                self.gauge('cassandra.replication_factor', int(round(percent_total / 100)),
                           tags=tags + ['keyspace:%s' % keyspace, 'datacenter:%s' % datacenter])

    def _process_nodetool_output(self, output):
        percent_up_by_datacenter = defaultdict(float)
        percent_total_by_datacenter = defaultdict(float)
        for line in output.splitlines():
            # Ouput of nodetool
            # Datacenter: dc1
            # ===============
            # Status=Up/Down
            # |/ State=Normal/Leaving/Joining/Moving
            # --  Address     Load       Tokens  Owns (effective)  Host ID                               Rack
            # UN  172.21.0.3  184.8 KB   256     38.4%             7501ef03-eb63-4db0-95e6-20bfeb7cdd87  RAC1
            # UN  172.21.0.4  223.34 KB  256     39.5%             e521a2a4-39d3-4311-a195-667bf56450f4  RAC1
            match = self.datacenter_name_re.search(line)
            if match:
                datacenter_name = match.group(1)
            match = self.host_status_re.search(line)
            if match:
                host_status = match.group('status')
                host_owns = match.group('owns')
                if host_status == 'U' and host_owns != '?':
                    percent_up_by_datacenter[datacenter_name] += float(host_owns[:-1])
                percent_total_by_datacenter[datacenter_name] += float(host_owns[:-1])

        return percent_up_by_datacenter, percent_total_by_datacenter
