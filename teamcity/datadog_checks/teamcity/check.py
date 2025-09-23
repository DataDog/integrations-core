# (C) Datadog, Inc. 2014-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck, is_affirmative

from .teamcity_openmetrics import TeamCityOpenMetrics


class TeamCityCheck(AgentCheck):
    __NAMESPACE__ = 'teamcity'

    def __new__(cls, name, init_config, instances):
        instance = instances[0]

        if is_affirmative(instance.get('use_openmetrics', False)):
            return TeamCityOpenMetrics(name, init_config, instances)
        else:
            from .teamcity_rest import TeamCityRest

            return TeamCityRest(name, init_config, instances)
