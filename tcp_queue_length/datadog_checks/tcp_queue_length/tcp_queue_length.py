# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import requests_unixsocket

from datadog_checks.base import AgentCheck

class TcpQueueLengthCheck(AgentCheck):

    NAMESPACE = "tcp_queue"

    def __init__(self, *args, **kwargs):
        super(AgentCheck, self).__init__(*args, **kwargs)
        self.session = requests_unixsocket.Session()

    def check(self, instance):
        try:
            r = self.session.get('http+unix://%2Fopt%2Fdatadog-agent%2Frun%2Fsysprobe.sock/probe/tcp_queue_length', timeout=10)
            r.raise_for_status()
        except Exception as e:
            self.log.warning('GET on system-probe socket failed: {}'.format(str(e)))
            return

        instance_tags = instance.get('tags', [])

        for line in r.json():
            try:
                tags = ['saddr:{}'.format(line['conn']['saddr']),
                        'daddr:{}'.format(line['conn']['daddr']),
                        'sport:{}'.format(line['conn']['sport']),
                        'dport:{}'.format(line['conn']['dport']),
                        'pid:{}'.format(line['stats']['pid'])]

                self.gauge(self.NAMESPACE + '.rqueue.min', float(line['stats']['read queue']['min']), instance_tags + tags)
                self.gauge(self.NAMESPACE + '.rqueue.max', float(line['stats']['read queue']['max']), instance_tags + tags)
                self.gauge(self.NAMESPACE + '.wqueue.min', float(line['stats']['write queue']['min']), instance_tags + tags)
                self.gauge(self.NAMESPACE + '.wqueue.max', float(line['stats']['write queue']['max']), instance_tags + tags)
            except KeyError as e:
                self.log.error('Invalid line received from `/probe/tcp_queue_length`: {}'.format(e))
