# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib

# 3rd party

# project
from checks import AgentCheck

EVENT_TYPE = SOURCE_TYPE_NAME = 'activemq'


class ActivemqCheck(AgentCheck):

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

    def check(self, instance):
        pass
