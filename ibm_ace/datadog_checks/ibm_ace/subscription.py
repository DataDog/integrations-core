# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import hashlib
import time
import traceback
from abc import ABC, abstractmethod

import pymqi

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.time import get_timestamp

from .flows import get_statistics
from .resources import get_resource

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

# https://www.ibm.com/docs/en/app-connect/12.0?topic=performance-resource-statistics
# https://www.ibm.com/docs/en/app-connect/12.0?topic=data-message-flow-accounting-statistics-collection-options
SNAPSHOT_UPDATE_INTERVAL = 20


def get_unique_name(check_id, topic_string):
    # https://www.ibm.com/docs/en/ibm-mq/9.2?topic=reference-crtmqmsub-create-mq-subscription#q084220___q084220SUBNAME
    hostname = datadog_agent.get_hostname()
    data = topic_string.encode('utf-8')
    return f'datadog-{check_id}-{hostname}-{hashlib.sha256(data).hexdigest()}'


class Subscription(ABC):
    TYPE: str
    TOPIC_STRING: str

    def __init__(self, check, tags):
        self.check = check
        self.tags = tags
        self.name = get_unique_name(check.check_id, self.TOPIC_STRING)

        self._options = pymqi.GMO(
            Options=pymqi.CMQC.MQGMO_NO_SYNCPOINT + pymqi.CMQC.MQGMO_FAIL_IF_QUIESCING + pymqi.CMQC.MQGMO_WAIT
        )

        self._last_execution_time = None
        self._sub = None

    @abstractmethod
    def collect(self):
        pass

    @abstractmethod
    def get_message_id(self, message):
        pass

    def get_latest_messages(self):
        if self._last_execution_time is None:
            self._last_execution_time = get_timestamp()

        message_cache = {}
        # Use as an ordered set
        unknown_errors = {}

        while True:
            try:
                payload = self.sub.get(None, pymqi.md(), self._get_options())
            except pymqi.MQMIError as e:
                if not (e.comp == pymqi.CMQC.MQCC_FAILED and e.reason == pymqi.CMQC.MQRC_NO_MSG_AVAILABLE):
                    unknown_errors[str(e)] = traceback.format_exc()
                    time.sleep(1)
            else:
                message = self.parse_message(payload)
                message_cache[self.get_message_id(message)] = message

            if self._get_elapsed_time() >= SNAPSHOT_UPDATE_INTERVAL:
                break

        tags = [f'subscription:{self.TYPE}', *self.tags]
        if unknown_errors:
            status_message = 'Subscription error for topic string: {}'.format(self.TOPIC_STRING)
            self._submit_health_status(ServiceCheck.CRITICAL, tags, status_message)
            for error in unknown_errors.values():
                self.check.log.error('%s\n%s', status_message, error)
        elif not message_cache:
            status_message = 'Subscription found nothing for topic string: {}'.format(self.TOPIC_STRING)
            self._submit_health_status(ServiceCheck.WARNING, tags, status_message)
            self.check.log.warning(status_message)
        else:
            self._submit_health_status(ServiceCheck.OK, tags)

        messages = list(message_cache.values())
        self.check.gauge('messages.current', len(messages), tags=tags)
        self.check.log.trace('Messages found for subscription type `%s`: %s', self.TYPE, messages)

        self._last_execution_time = get_timestamp()
        return messages

    def parse_message(self, payload):
        return json.loads(payload.decode('utf-8'))

    @property
    def sub(self):
        if self._sub is None:
            sub = pymqi.Subscription(self.check.queue_manager)
            # https://dsuch.github.io/pymqi/examples.html#how-to-subscribe-to-topics-and-avoid-mqrc-sub-already-exists-at-the-same-time
            self.check.log.debug('Subscribing to `%s` topic string: %s.', self.TYPE, self.TOPIC_STRING)
            sub.sub(
                sub_name=self.name,
                topic_string=self.TOPIC_STRING,
                sub_opts=(
                    pymqi.CMQC.MQSO_CREATE
                    + pymqi.CMQC.MQSO_RESUME
                    + pymqi.CMQC.MQSO_NON_DURABLE
                    + pymqi.CMQC.MQSO_MANAGED
                ),
            )
            self._sub = sub

        return self._sub

    def disconnect(self):
        if self._sub is not None:
            self._sub.close(sub_close_options=pymqi.CMQC.MQCO_REMOVE_SUB, close_sub_queue=True)
            self._sub = None

    def _submit_health_status(self, status, tags, message=None):
        self.check.service_check('mq.subscription', status, tags=tags, message=message)

    def _get_elapsed_time(self):
        return get_timestamp() - self._last_execution_time

    def _get_options(self):
        self._options['WaitInterval'] = int(max(2, SNAPSHOT_UPDATE_INTERVAL - self._get_elapsed_time()) * 1000)
        return self._options


class ResourceStatisticsSubscription(Subscription):
    TYPE = 'resource_statistics'
    TOPIC_STRING = '$SYS/Broker/+/Statistics/JSON/Resource/#'

    def get_message_id(self, message):
        data = message['ResourceStatistics']
        return data['brokerLabel'], data['executionGroupName']

    def collect(self):
        """
        https://www.ibm.com/docs/en/app-connect/12.0?topic=data-example-xml-publication-resource-statistics
        """
        messages = self.get_latest_messages()
        for message in messages:
            resource_statistics = message['ResourceStatistics']
            resource_tags = [
                f'integration_node:{resource_statistics["brokerLabel"]}',
                f'integration_server:{resource_statistics["executionGroupName"]}',
                *self.tags,
            ]

            for resource_data in resource_statistics['ResourceType']:
                resource = get_resource(resource_data['name'])

                for metric_data in resource_data['resourceIdentifier']:
                    tags = resource.parse_tags(resource_tags, metric_data)

                    for metric, value in metric_data.items():
                        resource.submit(self.check, metric, value, tags)


class FlowMonitoringSubscription(Subscription):
    TYPE = 'message_flows'
    TOPIC_STRING = '$SYS/Broker/+/Statistics/JSON/SnapShot/#/applications/#'

    def parse_message(self, payload):
        # The payloads are malformed so we must remove everything before the JSON:
        # RFH \x02\x00\x00\x00\xe4\x00\x00\x00"\x02\x00\x00\xb8\x04\x00\x00MQSTR   \x00\x00\x00...
        return super().parse_message(payload[payload.index(b'{') :])

    def get_message_id(self, message):
        data = message['WMQIStatisticsAccounting']['MessageFlow']
        return data['BrokerLabel'], data['ExecutionGroupName'], data['MessageFlowName']

    def collect(self):
        """
        https://www.ibm.com/docs/en/app-connect/12.0?topic=data-json-publication-message-flow-accounting-statistics
        """
        messages = self.get_latest_messages()
        for message in messages:
            for name, data in message['WMQIStatisticsAccounting'].items():
                statistics = get_statistics(name)
                if statistics is None:
                    self.check.log.debug(
                        'Not collecting flow statistic group: %s. Refer to the Datadog IBM ACE documentation for '
                        'list of collected metrics.',
                        name,
                    )
                    continue

                statistics.submit(self.check, data, self.tags)
