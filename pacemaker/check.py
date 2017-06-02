# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

"""ceph check
Collects metrics from pacemaker clusters
"""

import socket
from xml.etree import ElementTree as tree
from utils.subprocess_output import get_subprocess_output
from checks import AgentCheck


class PaceMaker(AgentCheck):

    NAMESPACE = 'pacemaker'
    DEFAULT_CRM_MON_CMD = '/usr/sbin/crm_mon'

    def _publish(self, value, func, key, tags):
        try:
            func(self.NAMESPACE + '.' + key, value, tags)
        except KeyError:
            return

    def _collect_raw(self, crm_mon_cmd):
	args = ['sudo', crm_mon_cmd, '-1', '--as-xml']
	try:
	    output,_,_ = get_subprocess_output(args, self.log)
	except Exception as e:
	    raise Exception('Unable to parse data from cmd=%s: %s' % (' '.join(args), str(e)))
	return tree.fromstring(output)


    def _extract_and_publish_metrics(self, xml_output, tags):
        data = {}

        # Collect online cluster nodes and resources running metrics
	online_nodes = 0
	nodes_status = xml_output.find('nodes')
	for node in nodes_status.iter():
	    if node.attrib:
		if node.attrib['online'] == 'true':
		    online_nodes += 1
            if node.attrib.get('name') == socket.gethostname():
                self._publish(node.attrib['resources_running'], self.gauge, 'resources_running', tags)
        self._publish(online_nodes, self.gauge, 'online_nodes', tags)
        data['online_nodes'] = int(online_nodes)

        # Collect nodes configured and resources configured metrics
	cluster_summary = xml_output.find('summary')
	for summ in cluster_summary.iter():
	    if summ.tag in ['nodes_configured']:
                self._publish(summ.attrib['number'], self.gauge, 'nodes_configured', tags)
                data['nodes_configured'] = int(summ.attrib['number'])
	    if summ.tag in ['resources_configured']:
                self._publish(summ.attrib['number'], self.gauge, 'resources_configured', tags)

        # Collect ban resources metric
        bans_count = len(xml_output.find('bans'))
        self._publish(bans_count, self.gauge, 'ban_resources', tags)
        data['ban_resources'] = int(bans_count)

        return data


    def _perform_service_checks(self, data):
        if (data['online_nodes'] == data['nodes_configured'] and data['ban_resources'] == 0):
            status = AgentCheck.OK
        elif (data['online_nodes'] == (data['nodes_configured'] - 1) or data['ban_resources'] > 0):
            status = AgentCheck.WARNING
        else:
            status = AgentCheck.CRITICAL
        self.service_check(self.NAMESPACE + '.overall_status', status)

    def check(self, instance):
        crm_mon_cmd = instance.get('crm_mon_cmd') or self.DEFAULT_CRM_MON_CMD
        tags = instance.get('tags', [])

        xml_output = self._collect_raw(crm_mon_cmd)
        data = self._extract_and_publish_metrics(xml_output, tags)
        self._perform_service_checks(data)
