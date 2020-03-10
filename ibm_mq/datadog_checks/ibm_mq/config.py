# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
import re
from typing import Dict, List, Pattern

from six import iteritems

from datadog_checks.base import AgentCheck
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.config import is_affirmative

# compatibility layer for agents under 6.6.0
try:
    from datadog_checks.errors import ConfigurationError
except ImportError:
    ConfigurationError = Exception

try:
    import pymqi
except ImportError:
    pymqi = None
else:
    # Since pymqi is not be available/installed on win/macOS when running e2e,
    # we load the following constants only pymqi import succeed

    DEFAULT_CHANNEL_STATUS_MAPPING = {
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


log = logging.getLogger(__file__)


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
        self.channel = instance.get('channel')  # type: str
        self.queue_manager_name = instance.get('queue_manager', 'default')  # type: str

        self.host = instance.get('host', 'localhost')  # type: str
        self.port = instance.get('port', '1414')  # type: str
        self.host_and_port = "{}({})".format(self.host, self.port)

        self.username = instance.get('username')  # type: str
        self.password = instance.get('password')  # type: str

        self.queues = instance.get('queues', [])  # type: List[str]
        self.queue_patterns = instance.get('queue_patterns', [])  # type: List[str]
        self.queue_regex = [re.compile(regex) for regex in instance.get('queue_regex', [])]  # type: List[Pattern]

        self.auto_discover_queues = is_affirmative(instance.get('auto_discover_queues', False))  # type: bool

        if int(self.auto_discover_queues) + int(bool(self.queue_patterns)) + int(bool(self.queue_regex)) > 1:
            log.warning(
                "Configurations auto_discover_queues, queue_patterns and queue_regex are not intended to be used "
                "together."
            )

        self.channels = instance.get('channels', [])  # type: List[str]

        self.channel_status_mapping = self.get_channel_status_mapping(
            instance.get('channel_status_mapping')
        )  # type: Dict[str, str]

        self.custom_tags = instance.get('tags', [])  # type: List[str]

        self.ssl = is_affirmative(instance.get('ssl_auth', False))  # type: bool
        self.ssl_cipher_spec = instance.get('ssl_cipher_spec', 'TLS_RSA_WITH_AES_256_CBC_SHA')  # type: str

        self.ssl_key_repository_location = instance.get(
            'ssl_key_repository_location', '/var/mqm/ssl-db/client/KeyringClient'
        )  # type: str

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

    def check_properly_configured(self):
        if not self.channel or not self.queue_manager_name or not self.host or not self.port:
            msg = "channel, queue_manager, host and port are all required configurations"
            raise ConfigurationError(msg)

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
                log.warning('%s is not a valid regular expression and will be ignored', regex_str)
        return queue_tag_list

    @property
    def tags(self):
        return [
            "queue_manager:{}".format(self.queue_manager_name),
            "mq_host:{}".format(self.host),  # 'host' is reserved and 'mq_host' is used instead
            "port:{}".format(self.port),
            "channel:{}".format(self.channel),
        ] + self.custom_tags

    @property
    def tags_no_channel(self):
        return [
            "queue_manager:{}".format(self.queue_manager_name),
            "mq_host:{}".format(self.host),  # 'host' is reserved and 'mq_host' is used instead
            "port:{}".format(self.port),
        ] + self.custom_tags

    @staticmethod
    def get_channel_status_mapping(channel_status_mapping_raw):
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
            return DEFAULT_CHANNEL_STATUS_MAPPING
