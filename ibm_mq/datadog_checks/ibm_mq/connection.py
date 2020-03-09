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
    cd = _get_channel_definition(config)
    queue_manager = pymqi.QueueManager(None)

    if config.username and config.password:
        log.debug("connecting with username and password")

        kwargs = {'user': config.username, 'password': config.password, 'cd': cd}

        queue_manager.connect_with_options(config.queue_manager_name, **kwargs)
    else:
        log.debug("connecting without a username and password")
        queue_manager.connect_with_options(config.queue_manager, cd)
    return queue_manager


def get_ssl_connection(config):
    """
    Get the connection with SSL
    """
    cd = _get_channel_definition(config)
    cd.SSLCipherSpec = config.ssl_cipher_spec

    sco = pymqi.SCO()
    sco.KeyRepository = config.ssl_key_repository_location

    queue_manager = pymqi.QueueManager(None)
    queue_manager.connect_with_options(config.queue_manager_name, cd, sco)

    return queue_manager


def _get_channel_definition(config):
    cd = pymqi.CD()
    cd.ChannelName = pymqi.ensure_bytes(config.channel)
    cd.ConnectionName = pymqi.ensure_bytes(config.host_and_port)
    cd.ChannelType = pymqi.CMQC.MQCHT_CLNTCONN
    cd.TransportType = pymqi.CMQC.MQXPT_TCP
    cd.Version = config.mqcd_version
    return cd
