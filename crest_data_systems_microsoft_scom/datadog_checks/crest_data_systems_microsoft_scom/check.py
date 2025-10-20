# Copyright (C) 2025 Crest Data.
# All rights reserved

from datadog_checks.base import AgentCheck


class CrestDataSystemsMicrosoftScomLogCrawlerCheck(AgentCheck):
    # This will be the prefix of every metric the integration sends
    __NAMESPACE__ = "crest_data_systems_microsoft_scom_log_crawler_check"

    def __init__(self, name, init_config, instances):
        """
        Initialize the CrestDataSystemsMicrosoftScomLogCrawlerCheck class.

        This class now extends LogCrawlerCheck for Agent-based log collection.
        It also sets the site to the default value
        if not provided in the configuration. Additionally, it sets the minimum
        collection interval to the value provided in the configuration. Finally,
        it initializes the Datadog client and calls the initialize_configurations
        method to set the rest of the configurations.

        Parameters:
            name (str): The name of the check.
            init_config (dict): The Datadog configuration.
            instances (list): The list of configurations for this check.
        """
        super(CrestDataSystemsMicrosoftScomLogCrawlerCheck, self).__init__(name, init_config, instances)
