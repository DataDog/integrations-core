# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


CORE_CHECK = f"""\
[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[3]:https://app.datadoghq.com/account/settings#agent
[4]: https://github.com/DataDog/integrations-core/blob/master/check/datadog_checks/check/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/check/metadata.csv
[8]: https://github.com/DataDog/integrations-core/blob/master/check/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
"""

CORE_LOGS = f"""\
[1]: https://docs.datadoghq.com/help/
[2]:https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[4]: **LINK_TO_INTEGRATION_SITE**
[5]: https://github.com/DataDog/integrations-core/blob/master/logs/assets/service_checks.json
"""

CORE_JMX = f"""\
[1]: **LINK_TO_INTEGERATION_SITE**
[2]:https://app.datadoghq.com/account/settings#agent
[3]: https://github.com/DataDog/integrations-core/blob/master/jmx/datadog_checks/jmx/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[5]: https://docs.datadoghq.com/integrations/java/
[6]: https://docs.datadoghq.com/help/
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[8]: https://github.com/DataDog/integrations-core/blob/master/jmx/assets/service_checks.json
"""

CORE_SNMP_TILE = f"""\
[1]: https://docs.datadoghq.com/network_performance_monitoring/devices/data
[2]: https://docs.datadoghq.com/network_performance_monitoring/devices/setup
[3]: https://github.com/DataDog/integrations-core/blob/master/snmp_tile/assets/service_checks.json
[4]: https://docs.datadoghq.com/help/
[5]: https://www.datadoghq.com/blog/monitor-snmp-with-datadog/
"""

CORE_TILE = f"""\
[1]: **LINK_TO_INTEGRATION_SITE**
[2]:https://app.datadoghq.com/account/settings#agent
[3]: https://docs.datadoghq.com/help/
"""
