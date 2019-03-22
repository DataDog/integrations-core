# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.config import is_affirmative

# compatability layer for agents under 6.6.0
try:
    from datadog_checks.errors import ConfigurationError
except ImportError:
    ConfigurationError = Exception


class IBMMQConfig:
    """
    A config object. Parse the instance and return it as an object that can be passed around
    No need to parse the instance more than once in the check run
    """

    DISALLOWED_QUEUES = [
        'SYSTEM.MQSC.REPLY.QUEUE',
        'SYSTEM.DEFAULT.MODEL.QUEUE',
        'SYSTEM.DURABLE.MODEL.QUEUE',
        'SYSTEM.JMS.TEMPQ.MODEL',
        'SYSTEM.MQEXPLORER.REPLY.MODEL',
        'SYSTEM.NDURABLE.MODEL.QUEUE',
        'SYSTEM.CLUSTER.TRANSMIT.MODEL.QUEUE',
    ]

    def __init__(self, instance):
        self.channel = instance.get('channel')
        self.queue_manager_name = instance.get('queue_manager', 'default')

        self.host = instance.get('host', 'localhost')
        self.port = instance.get('port', '1414')
        self.host_and_port = "{}({})".format(self.host, self.port)

        self.username = instance.get('username')
        self.password = instance.get('password')

        self.queues = instance.get('queues', [])
        self.queue_patterns = instance.get('queue_patterns', [])

        self.custom_tags = instance.get('tags', [])

        self.auto_discover_queues = is_affirmative(instance.get('auto_discover_queues', False))

        self.ssl = is_affirmative(instance.get('ssl_auth', False))
        self.ssl_cipher_spec = instance.get('ssl_cipher_spec', 'TLS_RSA_WITH_AES_256_CBC_SHA')

        self.ssl_key_repository_location = instance.get(
            'ssl_key_repository_location',
            '/var/mqm/ssl-db/client/KeyringClient'
        )

        self.mq_installation_dir = instance.get('mq_installation_dir', '/opt/mqm/')

    def check_properly_configured(self):
        if not self.channel or not self.queue_manager_name or not self.host or not self.port:
            msg = "channel, queue_manager, host and port are all required configurations"
            raise ConfigurationError(msg)

    def add_queues(self, new_queues):
        # add queues without duplication
        self.queues = list(set(self.queues + new_queues))

    @property
    def tags(self):
        return [
            "queue_manager:{}".format(self.queue_manager_name),
            "host:{}".format(self.host),
            "port:{}".format(self.port),
            "channel:{}".format(self.channel)
        ] + self.custom_tags
