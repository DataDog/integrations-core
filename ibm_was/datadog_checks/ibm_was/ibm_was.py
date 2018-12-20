# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import ConfigurationError
from datadog_checks.checks import AgentCheck

from lxml import etree


class IbmWasCheck(AgentCheck):

    def check(self, instance):
        self.validate_config(instance)
        data = self.make_request("servers")
        server_data_xml = etree.fromstring(data)
        self.log.debug(data)

    def make_request(url):
        pass

    def validate_config(self, instance):
        if not instance.get('servlet_url'):
            raise ConfigurationError("Please specify a servlet_url in the configuration file")
