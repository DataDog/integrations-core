# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# from datadog_checks.config import is_affirmative

# compatability layer for agents under 6.6.0
try:
    from datadog_checks.errors import ConfigurationError
except ImportError:
    ConfigurationError = Exception


class SslConfig:
    """
    A config object. Parse the instance and return it as an object that can be passed around
    No need to parse the instance more than once in the check run
    """

    def __init__(self, instance):
        self.name = instance.get('name')
        self.host = instance.get('host')
        self.port = instance.get('port')
        self.host_and_port = "{}({})".format(self.host, self.port)
        self.timeout = instance.get('timeout')
        self.days_warning = instance.get('days_warning', '14')
        self.days_critical = instance.get('days_critical', '14')
        self.check_hostname = instance.get('check_hostname', 'true')
        self.ssl_hostname = instance.get('ssl_hostname')
        self.custom_tags = instance.get('tags', [])

    # def check_properly_configured(self):
        # if not self.channel or not self.queue_manager_name or not self.host or not self.port:
        #     msg = "channel, queue_manager, host and port are all required configurations"
        #     raise ConfigurationError(msg)

    # def add_queues(self, new_queues):
        # add queues without duplication
        #        self.queues = list(set(self.queues + new_queues))

    @property
    def tags(self):
        return [
            "host:{}".format(self.host),
            "port:{}".format(self.port),
            "name:{}".format(self.name)
        ] + self.custom_tags
