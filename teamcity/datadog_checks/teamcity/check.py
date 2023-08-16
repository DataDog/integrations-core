# (C) Datadog, Inc. 2014-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six import PY2

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative


class TeamCityCheck(AgentCheck):
    __NAMESPACE__ = 'teamcity'

    def __new__(cls, name, init_config, instances):
        instance = instances[0]

        if is_affirmative(instance.get('use_openmetrics', False)):
            if PY2:
                raise ConfigurationError(
                    "This version of the integration is only available when using py3. "
                    "Check https://docs.datadoghq.com/agent/guide/agent-v6-python-3 "
                    "for more information or use the older style config."
                )
            # TODO: when we drop Python 2 move this import up top
            from .teamcity_openmetrics import TeamCityOpenMetrics

            return TeamCityOpenMetrics(name, init_config, instances)
        else:
            from .teamcity_rest import TeamCityRest

            return TeamCityRest(name, init_config, instances)
