# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from xml.etree import ElementTree

import requests
from six import iteritems

from datadog_checks.base import AgentCheck
from datadog_checks.base.config import _is_affirmative

QUEUE_URL = "/admin/xml/queues.jsp"
TOPIC_URL = "/admin/xml/topics.jsp"
SUBSCRIBER_URL = "/admin/xml/subscribers.jsp"

TOPIC_QUEUE_METRICS = {
    "consumerCount": "consumer_count",
    "dequeueCount": "dequeue_count",
    "enqueueCount": "enqueue_count",
    "size": "size",
}

SUBSCRIBER_TAGS = ["connectionId", "subscriptionName", "destinationName", "selector", "active"]

MAX_ELEMENTS = 300


class ActiveMQXML(AgentCheck):
    def check(self, _):
        url = self.instance.get("url")
        custom_tags = self.instance.get('tags', [])
        max_queues = int(self.instance.get("max_queues", MAX_ELEMENTS))
        max_topics = int(self.instance.get("max_topics", MAX_ELEMENTS))
        max_subscribers = int(self.instance.get("max_subscribers", MAX_ELEMENTS))
        detailed_queues = self.instance.get("detailed_queues", [])
        detailed_topics = self.instance.get("detailed_topics", [])
        detailed_subscribers = self.instance.get("detailed_subscribers", [])
        suppress_errors = _is_affirmative(self.instance.get("suppress_errors", False))

        tags = custom_tags + ["url:{0}".format(url)]

        self.log.debug("Processing ActiveMQ data for %s", url)
        data = self._fetch_data(url, QUEUE_URL, suppress_errors)
        if data:
            self._process_data(data, "queue", tags, max_queues, detailed_queues)

        data = self._fetch_data(url, TOPIC_URL, suppress_errors)
        if data:
            self._process_data(data, "topic", tags, max_topics, detailed_topics)

        data = self._fetch_data(url, SUBSCRIBER_URL, suppress_errors)
        if data:
            self._process_subscriber_data(data, tags, max_subscribers, detailed_subscribers)

    def _fetch_data(self, base_url, xml_url, suppress_errors):
        url = "%s%s" % (base_url, xml_url)
        self.log.debug("ActiveMQ Fetching queue data from: %s", url)
        try:
            r = self.http.get(url)
            r.raise_for_status()
        except requests.exceptions.ConnectionError:
            if suppress_errors:
                self.log.warning("ActiveMQ not contactable, but suppressing the error due to configuration.")
                return False
            else:
                raise
        return r.text

    def _process_data(self, data, el_type, tags, max_elements, detailed_elements):
        root = ElementTree.fromstring(data)
        # if list provided in config, only send those metrics
        if detailed_elements:
            elements = [e for e in root.findall(el_type) if e.get('name') in detailed_elements]
        else:
            elements = [e for e in root.findall(el_type) if e.get('name')]
        count = len(elements)

        if count > max_elements:
            if not detailed_elements:
                self.warning(
                    "Number of %s is too high (%s > %s). "
                    "Please use the detailed_%ss parameter"
                    " to list the %s you want to monitor.",
                    el_type,
                    count,
                    max_elements,
                    el_type,
                    el_type,
                )

        for el in elements[:max_elements]:
            name = el.get("name")
            stats = el.find("stats")
            if stats is None:
                continue

            el_tags = tags + ["{0}:{1}".format(el_type, name)]
            for attr_name, alias in iteritems(TOPIC_QUEUE_METRICS):
                metric_name = "activemq.{0}.{1}".format(el_type, alias)
                value = stats.get(attr_name, 0)
                self.gauge(metric_name, value, tags=el_tags)

        self.log.debug("ActiveMQ %s count: %s", el_type, count)
        self.gauge("activemq.{0}.count".format(el_type), count, tags=tags)

    def _process_subscriber_data(self, data, tags, max_subscribers, detailed_subscribers):
        root = ElementTree.fromstring(data)
        # if subscribers list provided in config, only send those metrics
        if detailed_subscribers:
            subscribers = [s for s in root.findall("subscriber") if s.get("clientId") in detailed_subscribers]
        else:
            subscribers = [s for s in root.findall("subscriber") if s.get("clientId")]

        count = len(subscribers)
        if count > max_subscribers:
            if not detailed_subscribers:
                self.warning(
                    "Number of subscribers is too high (%s > %s)."
                    "Please use the detailed_subscribers parameter "
                    "to list the %s you want to monitor.",
                    count,
                    max_subscribers,
                    count,
                )

        for subscriber in subscribers[:max_subscribers]:
            clientId = subscriber.get("clientId")
            if not clientId:
                continue
            subscribers.append(clientId)
            stats = subscriber.find("stats")
            if stats is None:
                continue

            el_tags = tags + ["clientId:{0}".format(clientId)]

            for name in SUBSCRIBER_TAGS:
                value = subscriber.get(name)
                if value is not None:
                    el_tags.append("%s:%s" % (name, value))

            pending_queue_size = stats.get("pendingQueueSize", 0)
            dequeue_counter = stats.get("dequeueCounter", 0)
            enqueue_counter = stats.get("enqueueCounter", 0)
            dispatched_queue_size = stats.get("dispatchedQueueSize", 0)
            dispatched_counter = stats.get("dispatchedCounter", 0)

            self.log.debug(
                "ActiveMQ Subscriber %s: %s %s %s %s %s",
                clientId,
                pending_queue_size,
                dequeue_counter,
                enqueue_counter,
                dispatched_queue_size,
                dispatched_counter,
            )
            self.gauge("activemq.subscriber.pending_queue_size", pending_queue_size, tags=el_tags)
            self.gauge("activemq.subscriber.dequeue_counter", dequeue_counter, tags=el_tags)
            self.gauge("activemq.subscriber.enqueue_counter", enqueue_counter, tags=el_tags)
            self.gauge("activemq.subscriber.dispatched_queue_size", dispatched_queue_size, tags=el_tags)
            self.gauge("activemq.subscriber.dispatched_counter", dispatched_counter, tags=el_tags)

        self.log.debug("ActiveMQ Subscriber Count: %s", count)
        self.gauge("activemq.subscriber.count", count, tags=tags)
