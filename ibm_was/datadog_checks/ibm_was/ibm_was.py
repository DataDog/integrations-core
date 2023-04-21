# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from xml.etree.ElementTree import ParseError

import requests
from lxml import etree
from six import iteritems

from datadog_checks.base import AgentCheck, ConfigurationError, ensure_unicode, is_affirmative

from . import metrics, validation


class IbmWasCheck(AgentCheck):

    SERVICE_CHECK_CONNECT = "ibm_was.can_connect"
    METRIC_PREFIX = 'ibm_was'

    def __init__(self, name, init_config, instances):
        super(IbmWasCheck, self).__init__(name, init_config, instances)
        self.metric_type_mapping = {
            'AverageStatistic': self.gauge,
            'BoundedRangeStatistic': self.gauge,
            'CountStatistic': self.monotonic_count,
            'DoubleStatistic': self.rate,
            'RangeStatistic': self.gauge,
            'TimeStatistic': self.gauge,
        }
        self.url = self.instance.get('servlet_url')
        self.custom_queries = self.instance.get('custom_queries', [])
        self.custom_queries_units_gauge = set(self.instance.get('custom_queries_units_gauge', []))
        self.custom_tags = self.instance.get('tags', [])
        self.collect_stats = self.setup_configured_stats()
        self.nested_tags, self.metric_categories = self.append_custom_queries()
        self.custom_stats = set(self.nested_tags)
        self.service_check_tags = self.custom_tags + ['url:{}'.format(self.url)]

        self.check_initializations.append(self._validate_config)

    def _validate_config(self):
        if not self.instance.get('servlet_url'):
            raise ConfigurationError("Please specify a servlet_url in the configuration file")

    def check(self, _):
        data = self.make_request()

        try:
            server_data_xml = etree.fromstring(data)
        except ParseError as e:
            self.submit_service_checks(AgentCheck.CRITICAL)
            self.log.Error("Unable to parse the XML response: {}".format(e))
            return

        node_list = self.get_node_from_root(server_data_xml, "Node")

        for node in node_list:
            server_list = self.get_node_from_root(node, 'Server')
            node_tags = list(self.custom_tags)

            node_tags.append('node:{}'.format(node.get('name')))
            for server in server_list:
                server_tags = ['server:{}'.format(server.get('name'))]
                server_tags.extend(node_tags)

                for category, prefix in iteritems(self.metric_categories):
                    if self.collect_stats.get(category):
                        self.log.debug("Collecting %s stats", category)
                        stats = self.get_node_from_name(server, category)
                        self.process_stats(stats, prefix, server_tags)

    def get_node_from_name(self, xml_data, path):
        # XMLPath returns a list, but there should only be one element here since the function starts
        # the search within a given Node/Server
        data = xml_data.xpath('.//Stat[normalize-space(@name)="{}"]'.format(path))
        if len(data):
            return data[0]
        else:
            self.log.debug('Error finding %s stats in XML output for server name `%s`.', path, xml_data.get('name'))
            return []

    def get_node_from_root(self, xml_data, path):
        return xml_data.findall(path)

    def process_stats(self, stats, prefix, tags, recursion_level=0):
        """
        The XML will have Stat Nodes and Nodes that contain the metrics themselves
        This code recursively goes through each Stat Node to properly setup tags
        where each Stat will have a different tag key depending on the context.
        """
        for child in stats:
            if child.tag in metrics.METRIC_VALUE_FIELDS:
                self.submit_metrics(child, prefix, tags)
            elif child.tag in metrics.CATEGORY_FIELDS:
                tag_list = self.nested_tags.get(prefix)
                if tag_list and len(tag_list) > recursion_level:
                    recursion_tags = tags + ['{}:{}'.format(tag_list[recursion_level], child.get('name'))]
                else:
                    recursion_tags = tags
                self.process_stats(child, prefix, recursion_tags, recursion_level + 1)

    def submit_metrics(self, child, prefix, tags):
        value = child.get(metrics.METRIC_VALUE_FIELDS[child.tag])
        metric_name = self.normalize(
            ensure_unicode(child.get('name')), prefix='{}.{}'.format(self.METRIC_PREFIX, prefix), fix_case=True
        )

        tag = child.tag
        if (
            child.get('unit') in self.custom_queries_units_gauge
            and prefix in self.custom_stats
            and tag == 'CountStatistic'
        ):
            tag = 'TimeStatistic'
        self.metric_type_mapping[tag](metric_name, value, tags=tags)

        # creates new JVM metrics correctly as gauges
        if prefix == "jvm":
            jvm_metric_name = "{}_gauge".format(metric_name)
            self.gauge(jvm_metric_name, value, tags=tags)

    def make_request(self):
        try:
            resp = self.http.get(self.url)
            resp.raise_for_status()
            self.submit_service_checks(AgentCheck.OK)
        except (requests.HTTPError, requests.ConnectionError) as e:
            self.warning(
                "Couldn't connect to URL: %s with exception: %s. Please verify the address is reachable", self.url, e
            )
            self.submit_service_checks(AgentCheck.CRITICAL)
            raise e
        return resp.content

    def submit_service_checks(self, value):
        self.gauge(self.SERVICE_CHECK_CONNECT, 1 if value == AgentCheck.OK else 0, tags=list(self.service_check_tags))
        self.service_check(self.SERVICE_CHECK_CONNECT, value, tags=list(self.service_check_tags))

    def append_custom_queries(self):
        custom_recursion_tags = {}
        custom_metric_categories = {}
        for query in self.custom_queries:
            validation.validate_query(query)
            custom_metric_categories[query['stat']] = query['metric_prefix']
            custom_recursion_tags[query['metric_prefix']] = list(query.get('tag_keys', []))
            self.collect_stats[query['stat']] = True
        return (
            dict(metrics.NESTED_TAGS, **custom_recursion_tags),
            dict(metrics.METRIC_CATEGORIES, **custom_metric_categories),
        )

    def setup_configured_stats(self):
        collect_stats = {}
        for category, prefix in iteritems(metrics.METRIC_CATEGORIES):
            if is_affirmative(self.instance.get('collect_{}_stats'.format(prefix), True)):
                collect_stats[category] = True
        return collect_stats
