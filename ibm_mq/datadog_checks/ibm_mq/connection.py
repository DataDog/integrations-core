# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import TYPE_CHECKING

from datadog_checks.ibm_mq.config import IBMMQConfig  # noqa: F401

try:
    import pymqi
except ImportError:
    pymqi = None

if TYPE_CHECKING:
    from datadog_checks.base.log import CheckLoggingAdapter  # noqa: F401


def get_queue_manager_connection(config, logger):
    # type: (IBMMQConfig, CheckLoggingAdapter) -> pymqi.QueueManager
    """
    Get the queue manager connection
    """
    if config.ssl:
        # There is a memory leak when SSL connections fail.
        # By testing with a normal connection first, we avoid making unnecessary SSL connections.
        # This does not fix the memory leak but mitigate its likelihood.
        # Details: https://github.com/dsuch/pymqi/issues/208
        if config.try_basic_auth:
            try:
                get_normal_connection(config, logger)
            except pymqi.MQMIError as e:
                logger.debug(
                    "Tried basic authentication before SSL connection to ensure channel exists."
                    "This is expected to fail with SSL or host unavailable errors. It failed with: %s",
                    e,
                )
                if e.reason == pymqi.CMQC.MQRC_UNKNOWN_CHANNEL_NAME:
                    raise
        return get_ssl_connection(config, logger)
    else:
        return get_normal_connection(config, logger)


def get_normal_connection(config, logger):
    # type: (IBMMQConfig, CheckLoggingAdapter) -> pymqi.QueueManager
    """
    Get the connection either with a username and password or without
    """
    channel_definition = _get_channel_definition(config)
    queue_manager = pymqi.QueueManager(None)

    if config.username and config.password:
        logger.debug("connecting with username and password")

        kwargs = {'user': config.username, 'password': config.password, 'cd': channel_definition}

        queue_manager.connect_with_options(config.queue_manager_name, **kwargs)
    else:
        logger.debug("connecting without a username and password")
        queue_manager.connect_with_options(config.queue_manager_name, channel_definition)
    return queue_manager


def get_ssl_connection(config, logger):
    # type: (IBMMQConfig, CheckLoggingAdapter) -> pymqi.QueueManager
    """
    Get the connection with SSL
    """
    cd = _get_channel_definition(config)
    cd.SSLCipherSpec = pymqi.ensure_bytes(config.ssl_cipher_spec)

    sco = pymqi.SCO()
    sco.KeyRepository = pymqi.ensure_bytes(config.ssl_key_repository_location)

    if config.ssl_certificate_label:
        sco.CertificateLabel = pymqi.ensure_bytes(config.ssl_certificate_label)

    connect_options = {}
    if config.username and config.password:
        connect_options.update(
            {
                'user': config.username,
                'password': config.password,
            }
        )

    logger.debug(
        "Create SSL connection with ConnectionName=%s, ChannelName=%s, Version=%s, SSLCipherSpec=%s, "
        "KeyRepository=%s, CertificateLabel=%s, user=%s",
        cd.ConnectionName,
        cd.ChannelName,
        cd.Version,
        cd.SSLCipherSpec,
        sco.KeyRepository,
        sco.CertificateLabel,
        connect_options.get('user'),
    )
    queue_manager = pymqi.QueueManager(None)
    queue_manager.connect_with_options(config.queue_manager_name, cd, sco, **connect_options)
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
