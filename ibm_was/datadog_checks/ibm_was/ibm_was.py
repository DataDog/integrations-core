# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import requests
from lxml import etree

from six import iteritems

from datadog_checks.base import AgentCheck, is_affirmative
from . import metrics, validation


class IbmWasCheck(AgentCheck):

    SERVICE_CHECK_CONNECT = "ibm_was.can_connect"

    def check(self, instance):
        self.collect_stats = {}
        validation.validate_config(instance)
        self.setup_config(instance)
        custom_recursion_tags, custom_metric_categories = self.setup_custom_queries(instance)
        metrics.RECURSION_TAGS = dict(metrics.RECURSION_TAGS, **custom_recursion_tags)
        metrics.METRIC_CATEGORIES = dict(metrics.METRIC_CATEGORIES, **custom_metric_categories)

        custom_tags = instance.get('custom_tags', [])

        data = self.make_request("servers")
        server_data_xml = etree.fromstring(data)
        node_list = self.get_node_from_root(server_data_xml, "Node")

        for node in node_list:
            server_list = self.get_node_from_root(node, 'Server')
            node_tags = list(custom_tags)
            node_tags.append('node:{}'.format(node.get('name')))

            for server in server_list:
                server_tags = ['server:{}'.format(server.get('name'))]
                server_tags.extend(node_tags)

                for category, prefix in iteritems(metrics.METRIC_CATEGORIES):
                    self.log.debug("Collecting {} stats".format(category))
                    if self.collect_stats.get(category):
                        stats = self.get_node_from_name(server, category)
                        self.process_stats(stats, prefix, server_tags)

    def get_node_from_name(self, xml_data, path):
        # XMLPath returns a list, but there should only be one element here since we start
        # the search within a given Node/server
        data = xml_data.xpath('//Stat[normalize-space(@name)="{}"]'.format(path))
        if len(data):
            return data[0]
        else:
            self.warning('Error finding {} stats in XML output.'.format(path))
            return []

    def get_node_from_root(self, xml_data, path):
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

    def setup_custom_queries(self, instance):
        custom_recursion_tags = {}
        custom_metric_categories = {}
        custom_queries = instance.get('custom_queries')
        for query in custom_queries:
            validation.validate_query(query)
            custom_metric_categories[query['stat']] = query['metric_prefix']
            custom_recursion_tags[query['metric_prefix']] = [key for key in query['tagKeys']]
        return custom_recursion_tags, custom_metric_categories

    def setup_config(self, instance):
        for category, prefix in iteritems(metrics.METRIC_CATEGORIES):
            if is_affirmative(instance.get('collect_{}_stats'.format(prefix), True)):
                self.collect_stats[category] = True
