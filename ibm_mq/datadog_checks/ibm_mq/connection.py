# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging

try:
    import pymqi
except ImportError:
    pymqi = None

log = logging.getLogger(__file__)


def get_queue_manager_connection(config):
    """
    Get the queue manager connection
    """
    if config.ssl:
        return get_ssl_connection(config)
    else:
        return get_normal_connection(config)


def get_normal_connection(config):
    """
    Get the connection either with a username and password or without
    """
    if config.username and config.password:
        log.debug("connecting with username and password")
        queue_manager = pymqi.connect(
            config.queue_manager_name, config.channel, config.host_and_port, config.username, config.password
        )
    else:
        log.debug("connecting without a username and password")
        queue_manager = pymqi.connect(config.queue_manager_name, config.channel, config.host_and_port)

    return queue_manager


def get_ssl_connection(config):
    """
    Get the connection with SSL
    """
    cd = pymqi.CD()
    cd.ChannelName = config.channel
    cd.ConnectionName = config.host_and_port
    cd.ChannelType = pymqi.CMQC.MQCHT_CLNTCONN
    cd.TransportType = pymqi.CMQC.MQXPT_TCP
    cd.SSLCipherSpec = config.ssl_cipher_spec

    sco = pymqi.SCO()
    sco.KeyRepository = config.ssl_key_repository_location

    queue_manager = pymqi.QueueManager(None)
    queue_manager.connect_with_options(config.queue_manager_name, cd, sco)

    return queue_manager
