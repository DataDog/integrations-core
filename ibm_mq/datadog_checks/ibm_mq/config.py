# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import datetime as dt
import re

from dateutil.tz import UTC
from six import PY2, iteritems

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.log import get_check_logger

try:
    from typing import Dict, List, Pattern  # noqa: F401
except ImportError:
    pass

try:
    import pymqi
except ImportError as e:
    pymqiException = e
    pymqi = None


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

    def __init__(self, instance, init_config):
        self.log = get_check_logger()
        self.channel = instance.get('channel')  # type: str
        self.queue_manager_name = instance.get('queue_manager', 'default')  # type: str

        if not self.channel or not self.queue_manager_name:
            msg = "channel, queue_manager are required configurations"
            raise ConfigurationError(msg)

        host = instance.get('host')  # type: str
        port = instance.get('port')  # type: str
        override_hostname = is_affirmative(instance.get('override_hostname', False))  # type: bool

        self.connection_name = instance.get('connection_name')  # type: str
        if (host or port) and self.connection_name:
            raise ConfigurationError(
                'Specify only one host/port or connection_name configuration, '
                '(host={}, port={}, connection_name={}).'.format(host, port, self.connection_name)
            )
        if override_hostname and self.connection_name:
            raise ConfigurationError(
                'You cannot override the hostname if you provide a `connection_name` instead of a `host`'
            )
        if override_hostname and not host:
            raise ConfigurationError("You cannot override the hostname if you don't provide a `host`")

        if not self.connection_name:
            host = host or 'localhost'
            port = port or '1414'
            self.connection_name = "{}({})".format(host, port)

        self.hostname = host if override_hostname else None
        self.username = instance.get('username')  # type: str
        self.password = instance.get('password')  # type: str
        self.timeout = int(float(instance.get('timeout', 5)) * 1000)  # type: int

        self.queues = instance.get('queues', [])  # type: List[str]
        self.queue_patterns = instance.get('queue_patterns', [])  # type: List[str]
        self.queue_regex = [re.compile(regex) for regex in instance.get('queue_regex', [])]  # type: List[Pattern]

        self.auto_discover_queues = is_affirmative(instance.get('auto_discover_queues', False))  # type: bool

        self.collect_statistics_metrics = is_affirmative(
            instance.get('collect_statistics_metrics', False)
        )  # type: bool
        self.collect_reset_queue_metrics = is_affirmative(instance.get('collect_reset_queue_metrics', True))
        if int(self.auto_discover_queues) + int(bool(self.queue_patterns)) + int(bool(self.queue_regex)) > 1:
            self.log.warning(
                "Configurations auto_discover_queues, queue_patterns and queue_regex are not intended to be used "
                "together."
            )

        self.channels = instance.get('channels', [])  # type: List[str]

        self.channel_status_mapping = self.get_channel_status_mapping(
            instance.get('channel_status_mapping')
        )  # type: Dict[str, str]

        self.convert_endianness = instance.get('convert_endianness', False)  # type: bool
        self.qm_timezone = instance.get('queue_manager_timezone', 'UTC')  # type: str
        self.auto_discover_channels = instance.get('auto_discover_channels', True)  # type: bool

        custom_tags = instance.get('tags', [])  # type: List[str]
        tags = [
            "queue_manager:{}".format(self.queue_manager_name),
            "connection_name:{}".format(self.connection_name),
        ]  # type: List[str]
        tags.extend(custom_tags)
        if host or port:
            if not override_hostname:
                # 'host' is reserved and 'mq_host' is used instead
                tags.append("mq_host:{}".format(host))
            else:
                self.log.debug("Overriding hostname with `%s`", host)
            tags.append("port:{}".format(port))
        self.tags_no_channel = tags
        self.tags = tags + ["channel:{}".format(self.channel)]  # type: List[str]

        # SSL options
        self.ssl = is_affirmative(instance.get('ssl_auth', False))  # type: bool
        self.try_basic_auth = is_affirmative(instance.get('try_basic_auth', True))  # type: bool
        self.ssl_cipher_spec = instance.get('ssl_cipher_spec', '')  # type: str
        self.ssl_key_repository_location = instance.get(
            'ssl_key_repository_location', '/var/mqm/ssl-db/client/KeyringClient'
        )  # type: str
        self.ssl_certificate_label = instance.get('ssl_certificate_label')  # type: str

        ssl_options = ['ssl_cipher_spec', 'ssl_key_repository_location', 'ssl_certificate_label']

        # Implicitly enable SSL auth connection if SSL options are used and `ssl_auth` isn't set
        if instance.get('ssl_auth') is None:
            if any([instance.get(o) for o in ssl_options]):
                self.log.info(
                    "`ssl_auth` has not been explicitly enabled but other SSL options have been provided. "
                    "SSL will be used for connecting"
                )
                self.ssl = True

        # Explicitly disable SSL auth connection if SSL options are used but `ssl_auth` is False
        if instance.get('ssl_auth') is False:
            if any([instance.get(o) for o in ssl_options]):
                self.log.warning(
                    "`ssl_auth` is explicitly disabled but SSL options are being used. "
                    "SSL will not be used for connecting."
                )

        self.mq_installation_dir = instance.get('mq_installation_dir', '/opt/mqm/')

        self._queue_tag_re = instance.get('queue_tag_re', {})  # type: Dict[str, str]
        self.queue_tag_re = self._compile_tag_re()

        raw_mqcd_version = instance.get('mqcd_version', 6)
        try:
            self.mqcd_version = getattr(pymqi.CMQC, 'MQCD_VERSION_{}'.format(raw_mqcd_version))  # type: int
        except (ValueError, AttributeError):
            raise ConfigurationError(
                "mqcd_version must be a number between 1 and 9. {} found.".format(raw_mqcd_version)
            )

        pattern = instance.get('queue_manager_process', init_config.get('queue_manager_process', ''))
        if pattern:
            if PY2:
                raise ConfigurationError('The `queue_manager_process` option is only supported on Agent 7')

            pattern = pattern.replace('<queue_manager>', re.escape(self.queue_manager_name))
            self.queue_manager_process_pattern = re.compile(pattern)

            # Implied immunity to IBM MQ's memory leak
            self.try_basic_auth = is_affirmative(instance.get('try_basic_auth', False))  # type: bool
        else:
            self.queue_manager_process_pattern = None

        self.instance_creation_datetime = dt.datetime.now(UTC)

    def add_queues(self, new_queues):
        # add queues without duplication
        self.queues = list(set(self.queues + new_queues))

    def _compile_tag_re(self):
        """
        Compile regex strings from queue_tag_re option and return list of compiled regex/tag pairs
        """
        queue_tag_list = []
        for regex_str, tags in iteritems(self._queue_tag_re):
            try:
                queue_tag_list.append([re.compile(regex_str), [t.strip() for t in tags.split(',')]])
            except TypeError:
                self.log.warning('%s is not a valid regular expression and will be ignored', regex_str)
        return queue_tag_list

    @staticmethod
    def get_channel_status_mapping(channel_status_mapping_raw):
        if pymqi is None:
            raise pymqiException
        if channel_status_mapping_raw:
            custom_mapping = {}
            for ibm_mq_status_raw, service_check_status_raw in channel_status_mapping_raw.items():
                ibm_mq_status_attr = 'MQCHS_{}'.format(ibm_mq_status_raw).upper()
                service_check_status_attr = service_check_status_raw.upper()

                if service_check_status_attr not in ServiceCheck._fields:
                    raise ConfigurationError("Invalid service check status: {}".format(service_check_status_raw))

                try:
                    custom_mapping[getattr(pymqi.CMQCFC, ibm_mq_status_attr)] = getattr(
                        AgentCheck, service_check_status_attr
                    )
                except AttributeError as e:
                    raise ConfigurationError("Invalid mapping: {}".format(e))
            return custom_mapping
        else:
            # Use a default mapping. (Can't be defined at top-level because pymqi may not be installed.)
            return {
                pymqi.CMQCFC.MQCHS_INACTIVE: AgentCheck.CRITICAL,
                pymqi.CMQCFC.MQCHS_BINDING: AgentCheck.WARNING,
                pymqi.CMQCFC.MQCHS_STARTING: AgentCheck.WARNING,
                pymqi.CMQCFC.MQCHS_RUNNING: AgentCheck.OK,
                pymqi.CMQCFC.MQCHS_STOPPING: AgentCheck.CRITICAL,
                pymqi.CMQCFC.MQCHS_RETRYING: AgentCheck.WARNING,
                pymqi.CMQCFC.MQCHS_STOPPED: AgentCheck.CRITICAL,
                pymqi.CMQCFC.MQCHS_REQUESTING: AgentCheck.WARNING,
                pymqi.CMQCFC.MQCHS_PAUSED: AgentCheck.WARNING,
                pymqi.CMQCFC.MQCHS_INITIALIZING: AgentCheck.WARNING,
            }
