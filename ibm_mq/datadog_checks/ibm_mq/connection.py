# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging

from pymqi import QueueManager

from datadog_checks.ibm_mq.config import IBMMQConfig

try:
    import pymqi
except ImportError:
    pymqi = None

log = logging.getLogger(__file__)


def get_queue_manager_connection(config):
    # type: (IBMMQConfig) -> QueueManager
    """
    Get the queue manager connection
    """
    if config.ssl:
        return get_ssl_connection(config)
    else:
        return get_normal_connection(config)


def get_normal_connection(config):
    # type: (IBMMQConfig) -> QueueManager
    """
    Get the connection either with a username and password or without
    """
    channel_definition = _get_channel_definition(config)
    queue_manager = pymqi.QueueManager(None)

    if config.username and config.password:
        log.debug("connecting with username and password")

        kwargs = {'user': config.username, 'password': config.password, 'cd': channel_definition}

        queue_manager.connect_with_options(config.queue_manager_name, **kwargs)
    else:
        log.debug("connecting without a username and password")
        queue_manager.connect_with_options(config.queue_manager_name, channel_definition)
    return queue_manager


def get_ssl_connection(config):
    # type: (IBMMQConfig) -> QueueManager
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
    # type: (IBMMQConfig) -> pymqi.CD
    cd = pymqi.CD()
    cd.ChannelName = pymqi.ensure_bytes(config.channel)
    cd.ConnectionName = pymqi.ensure_bytes(config.connection_name)
    cd.ChannelType = pymqi.CMQC.MQCHT_CLNTCONN
    cd.TransportType = pymqi.CMQC.MQXPT_TCP
    cd.Version = config.mqcd_version
    return cd
