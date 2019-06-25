# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging

try:
    import pymqi
except ImportError:
    pymqi = None

log = logging.getLogger(__file__)


class Connection:
    def __init__(self, config):
        self.config = config

    def get_queue_manager_pcf_connection(self):
        """
        Get the queue manager connection
        """
        if self.config.ssl:
            return self._get_ssl_connection()
        else:
            return self._get_normal_connection()

    def _get_normal_connection(self):
        """
        Get the connection either with a username and password or without
        """
        if self.config.username and self.config.password:
            log.debug("connecting with username and password")
            queue_manager = pymqi.connect(
                self.config.queue_manager_name,
                self.config.channel,
                self.config.host_and_port,
                self.config.username,
                self.config.password,
            )
        else:
            log.debug("connecting without a username and password")
            queue_manager = pymqi.connect(
                self.config.queue_manager_name, self.config.channel, self.config.host_and_port
            )

        return queue_manager

    def _get_ssl_connection(self):
        """
        Get the connection with SSL
        """
        cd = pymqi.CD()
        cd.ChannelName = self.config.channel
        cd.ConnectionName = self.config.host_and_port
        cd.ChannelType = pymqi.CMQC.MQCHT_CLNTCONN
        cd.TransportType = pymqi.CMQC.MQXPT_TCP
        cd.SSLCipherSpec = self.config.ssl_cipher_spec

        sco = pymqi.SCO()
        sco.KeyRepository = self.config.ssl_key_repository_location

        queue_manager = pymqi.QueueManager(None)
        queue_manager.connect_with_options(self.config.queue_manager_name, cd, sco)

        return queue_manager
