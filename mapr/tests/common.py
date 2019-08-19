# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


INSTANCE = {
    'mapr_host': 'mapr-lab-2-ghs6.c.datadog-integrations-lab.internal',
    'topic_path': '/var/mapr/mapr.monitoring/metricstreams',
    'whitelist': ['*'],
    'mapr_ticketfile_location': 'foo',
}

KAFKA_METRIC = {
    u'metric': u'mapr.process.context_switch_involuntary',
    u'value': 6308,
    u'tags': {
        u'clustername': u'demo',
        u'process_name': u'apiserver',
        u'clusterid': u'7616098736519857348',
        u'fqdn': u'mapr-lab-2-ghs6.c.datadog-integrations-lab.internal',
    },
}
