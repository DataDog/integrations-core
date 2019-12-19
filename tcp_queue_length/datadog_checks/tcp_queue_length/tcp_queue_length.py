# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import requests_unixsocket

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.tagging import tagger

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
                tags = copy.deepcopy(instance_tags)

                cid = line.get('containerid')
                if cid:
                    tags += tagger.tag('container_id://{}'.format(cid), tagger.ORCHESTRATOR)

                tags += ['saddr:{}'.format(line['conn']['saddr']),
                         'daddr:{}'.format(line['conn']['daddr']),
                         'sport:{}'.format(line['conn']['sport']),
                         'dport:{}'.format(line['conn']['dport']),
                         'pid:{}'.format(line['stats']['pid'])]

                self.gauge(self.NAMESPACE + '.rqueue.size', float(line['stats'][ 'read queue']['size']), tags)
                self.gauge(self.NAMESPACE + '.rqueue.min',  float(line['stats'][ 'read queue']['min']),  tags)
                self.gauge(self.NAMESPACE + '.rqueue.max',  float(line['stats'][ 'read queue']['max']),  tags)
                self.gauge(self.NAMESPACE + '.wqueue.size', float(line['stats']['write queue']['size']), tags)
                self.gauge(self.NAMESPACE + '.wqueue.min',  float(line['stats']['write queue']['min']),  tags)
                self.gauge(self.NAMESPACE + '.wqueue.max',  float(line['stats']['write queue']['max']),  tags)
            except KeyError as e:
                self.log.error('Invalid line received from `/probe/tcp_queue_length`: {}'.format(e))
