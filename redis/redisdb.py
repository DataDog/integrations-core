# stdlib

# 3rd party

# project
from checks import AgentCheck

EVENT_TYPE = SOURCE_TYPE_NAME = 'skeleton'


class SkeletonCheck(AgentCheck):

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

    def check(self, instance):
        pass
