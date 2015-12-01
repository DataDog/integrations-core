from checks import AgentCheck


class Personal(AgentCheck):

    def __init__(self, name, init_config, agent_config, instances=None):
        AgentCheck.__init__(self, name, init_config, agent_config, instances)

    def check(self, instance):
        # Metadata collection
        self.gauge('dd.tristan.test', 1)
