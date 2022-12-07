# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
METRICS_CONFIG = {
    'NTDS': {
        'name': 'ntds',
        'counters': [
            {
                'DRA Inbound Bytes Compressed (Between Sites, After Compression)/sec': {
                    'metric_name': 'dra.inbound.bytes.after_compression'
                },
                'DRA Inbound Bytes Compressed (Between Sites, Before Compression)/sec': {
                    'metric_name': 'dra.inbound.bytes.before_compression'
                },
                'DRA Inbound Bytes Not Compressed (Within Site)/sec': {
                    'metric_name': 'dra.inbound.bytes.not_compressed'
                },
                'DRA Inbound Bytes Total/sec': {'metric_name': 'dra.inbound.bytes.total'},
                'DRA Inbound Full Sync Objects Remaining': {'metric_name': 'dra.inbound.objects.remaining'},
                'DRA Inbound Objects/sec': {'metric_name': 'dra.inbound.objects.persec'},
                'DRA Inbound Objects Applied/sec': {'metric_name': 'dra.inbound.objects.applied_persec'},
                'DRA Inbound Objects Filtered/sec': {'metric_name': 'dra.inbound.objects.filtered_persec'},
                'DRA Inbound Object Updates Remaining in Packet': {
                    'metric_name': 'dra.inbound.objects.remaining_in_packet'
                },
                'DRA Inbound Properties Applied/sec': {'metric_name': 'dra.inbound.properties.applied_persec'},
                'DRA Inbound Properties Filtered/sec': {'metric_name': 'dra.inbound.properties.filtered_persec'},
                'DRA Inbound Properties Total/sec': {'metric_name': 'dra.inbound.properties.total_persec'},
                'DRA Inbound Values (DNs only)/sec': {'metric_name': 'dra.inbound.values.dns_persec'},
                'DRA Inbound Values Total/sec': {'metric_name': 'dra.inbound.values.total_persec'},
                'DRA Outbound Bytes Compressed (Between Sites, After Compression)/sec': {
                    'metric_name': 'dra.outbound.bytes.after_compression'
                },
                'DRA Outbound Bytes Compressed (Between Sites, Before Compression)/sec': {
                    'metric_name': 'dra.outbound.bytes.before_compression'
                },
                'DRA Outbound Bytes Not Compressed (Within Site)/sec': {
                    'metric_name': 'dra.outbound.bytes.not_compressed'
                },
                'DRA Outbound Bytes Total/sec': {'metric_name': 'dra.outbound.bytes.total'},
                'DRA Outbound Objects Filtered/sec': {'metric_name': 'dra.outbound.objects.filtered_persec'},
                'DRA Outbound Objects/sec': {'metric_name': 'dra.outbound.objects.persec'},
                'DRA Outbound Properties/sec': {'metric_name': 'dra.outbound.properties.persec'},
                'DRA Outbound Values (DNs only)/sec': {'metric_name': 'dra.outbound.values.dns_persec'},
                'DRA Outbound Values Total/sec': {'metric_name': 'dra.outbound.values.total_persec'},
                'DRA Pending Replication Synchronizations': {'metric_name': 'dra.replication.pending_synchronizations'},
                'DRA Sync Requests Made': {'metric_name': 'dra.sync_requests_made'},
                'DS Threads in Use': {'metric_name': 'ds.threads_in_use'},
                'LDAP Client Sessions': {'metric_name': 'ldap.client_sessions'},
                'LDAP Bind Time': {'metric_name': 'ldap.bind_time'},
                'LDAP Successful Binds/sec': {'metric_name': 'ldap.successful_binds_persec'},
                'LDAP Searches/sec': {'metric_name': 'ldap.searches_persec'},
            }
        ],
    },
}

DEFAULT_COUNTERS = [
    # counterset, instance of counter, counter name, metric name
    # This set is from the Microsoft recommended counters to monitor active directory:
    # https://technet.microsoft.com/en-us/library/cc961942.aspx
    [
        'NTDS',
        None,
        'DRA Inbound Bytes Compressed (Between Sites, After Compression)/sec',
        'active_directory.dra.inbound.bytes.after_compression',
        'gauge',
    ],
    [
        'NTDS',
        None,
        'DRA Inbound Bytes Compressed (Between Sites, Before Compression)/sec',
        'active_directory.dra.inbound.bytes.before_compression',
        'gauge',
    ],
    [
        'NTDS',
        None,
        'DRA Inbound Bytes Not Compressed (Within Site)/sec',
        'active_directory.dra.inbound.bytes.not_compressed',
        'gauge',
    ],
    ['NTDS', None, 'DRA Inbound Bytes Total/sec', 'active_directory.dra.inbound.bytes.total', 'gauge'],
    [
        'NTDS',
        None,
        'DRA Inbound Full Sync Objects Remaining',
        'active_directory.dra.inbound.objects.remaining',
        'gauge',
    ],
    ['NTDS', None, 'DRA Inbound Objects/sec', 'active_directory.dra.inbound.objects.persec', 'gauge'],
    ['NTDS', None, 'DRA Inbound Objects Applied/sec', 'active_directory.dra.inbound.objects.applied_persec', 'gauge'],
    ['NTDS', None, 'DRA Inbound Objects Filtered/sec', 'active_directory.dra.inbound.objects.filtered_persec', 'gauge'],
    [
        'NTDS',
        None,
        'DRA Inbound Object Updates Remaining in Packet',
        'active_directory.dra.inbound.objects.remaining_in_packet',
        'gauge',
    ],
    [
        'NTDS',
        None,
        'DRA Inbound Properties Applied/sec',
        'active_directory.dra.inbound.properties.applied_persec',
        'gauge',
    ],
    [
        'NTDS',
        None,
        'DRA Inbound Properties Filtered/sec',
        'active_directory.dra.inbound.properties.filtered_persec',
        'gauge',
    ],
    ['NTDS', None, 'DRA Inbound Properties Total/sec', 'active_directory.dra.inbound.properties.total_persec', 'gauge'],
    ['NTDS', None, 'DRA Inbound Values (DNs only)/sec', 'active_directory.dra.inbound.values.dns_persec', 'gauge'],
    ['NTDS', None, 'DRA Inbound Values Total/sec', 'active_directory.dra.inbound.values.total_persec', 'gauge'],
    [
        'NTDS',
        None,
        'DRA Outbound Bytes Compressed (Between Sites, After Compression)/sec',
        'active_directory.dra.outbound.bytes.after_compression',
        'gauge',
    ],
    [
        'NTDS',
        None,
        'DRA Outbound Bytes Compressed (Between Sites, Before Compression)/sec',
        'active_directory.dra.outbound.bytes.before_compression',
        'gauge',
    ],
    [
        'NTDS',
        None,
        'DRA Outbound Bytes Not Compressed (Within Site)/sec',
        'active_directory.dra.outbound.bytes.not_compressed',
        'gauge',
    ],
    ['NTDS', None, 'DRA Outbound Bytes Total/sec', 'active_directory.dra.outbound.bytes.total', 'gauge'],
    [
        'NTDS',
        None,
        'DRA Outbound Objects Filtered/sec',
        'active_directory.dra.outbound.objects.filtered_persec',
        'gauge',
    ],
    ['NTDS', None, 'DRA Outbound Objects/sec', 'active_directory.dra.outbound.objects.persec', 'gauge'],
    ['NTDS', None, 'DRA Outbound Properties/sec', 'active_directory.dra.outbound.properties.persec', 'gauge'],
    ['NTDS', None, 'DRA Outbound Values (DNs only)/sec', 'active_directory.dra.outbound.values.dns_persec', 'gauge'],
    ['NTDS', None, 'DRA Outbound Values Total/sec', 'active_directory.dra.outbound.values.total_persec', 'gauge'],
    [
        'NTDS',
        None,
        'DRA Pending Replication Synchronizations',
        'active_directory.dra.replication.pending_synchronizations',
        'gauge',
    ],
    ['NTDS', None, 'DRA Sync Requests Made', 'active_directory.dra.sync_requests_made', 'gauge'],
    ['NTDS', None, 'DS Threads in Use', 'active_directory.ds.threads_in_use', 'gauge'],
    ['NTDS', None, 'LDAP Client Sessions', 'active_directory.ldap.client_sessions', 'gauge'],
    ['NTDS', None, 'LDAP Bind Time', 'active_directory.ldap.bind_time', 'gauge'],
    ['NTDS', None, 'LDAP Successful Binds/sec', 'active_directory.ldap.successful_binds_persec', 'gauge'],
    ['NTDS', None, 'LDAP Searches/sec', 'active_directory.ldap.searches_persec', 'gauge'],
]
