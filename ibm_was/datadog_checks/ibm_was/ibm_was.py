# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import requests
from lxml import etree

from six import iteritems

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from . import metrics


class IbmWasCheck(AgentCheck):

    SERVICE_CHECK_CONNECT = "ibm_was.can_connect"

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.collect_stats = {}

    def check(self, instance):
        self.validate_config(instance)
        self.setup_config(instance)
        custom_tags = instance.get('custom_tags', [])

        data = self.make_request("servers")
        server_data_xml = etree.fromstring(data)
        node_list = self.get_path_from_element(server_data_xml, "Node")

        for node in node_list:
            server_list = self.get_path_from_element(node, 'Server')
            node_tags = list(custom_tags)
            node_tags.append('node:{}'.format(node.get('name')))

            for server in server_list:
                server_tags = ['server:{}'.format(server.get('name'))]
                server_tags.extend(node_tags)

                for category, prefix in iteritems(metrics.METRIC_CATEGORIES):
                    self.log.debug("Collecting {} stats".format(category))
                    if self.collect_stats[category]:
                        stats = self.get_xml_path(server, category)
                        self.process_stats(stats, prefix, server_tags)

    def get_xml_path(self, xml_data, path):
        # XMLPath returns a list, but there should only be one element here since we start
        # the search within a given Node/server
        data = xml_data.xpath('//Stat[normalize-space(@name)="{}"]'.format(path))
        if len(data):
            return data[0]
        else:
            self.warning('Error finding {} stats in XML output.'.format(path))
            return []

    def get_path_from_element(self, xml_data, path):
        return xml_data.xpath('//{}'.format(path))

    # The XML will have Stat Nodes and Nodes that contain the metrics themselves
    # We have to recursively go through each Stat Node to properly setup tags
    # where each Stat will have a different tag key depending on the context.
    def process_stats(self, stats, prefix, tags, recursion_level=0):
        for child in stats:
            if child.tag in metrics.METRIC_TAGS:
                self.submit_metrics(child, prefix, tags)
            elif child.tag in metrics.CATEGORY_TAGS:
                recursion_tags = tags + ["{}:{}".format(
                    metrics.RECURSION_TAGS.get(prefix)[recursion_level], child.get('name')
                )]
                self.process_stats(child, prefix, recursion_tags, recursion_level+1)

    def submit_metrics(self, child, prefix, tags):
        value = child.get(metrics.METRIC_TAGS[child.tag])
        self.gauge('ibmwas.{}.{}'.format(prefix, child.get('name')), value, tags=tags)

    def make_request(self, url):
        try:
            resp = requests.get(url)
            resp.raise_for_status()
            self.service_check(self.SERVICE_CHECK_CONNECT, AgentCheck.OK, tags='url')
        except requests.HTTPError as e:
            self.warning(
                "Couldn't connect to URL: {} with exception: {}. Please verify the address is reachable"
                .format(url, e))
            self.service_check(self.SERVICE_CHECK_CONNECT, AgentCheck.CRITICAL, tags='url')
        return resp

    def validate_config(self, instance):
        if not instance.get('servlet_url'):
            raise ConfigurationError("Please specify a servlet_url in the configuration file")

    def setup_config(self, instance):
        for category, prefix in iteritems(metrics.METRIC_CATEGORIES):
            if is_affirmative(instance.get('collect_{}_stats'.format(prefix), True)):
                self.collect_stats[category] = True
