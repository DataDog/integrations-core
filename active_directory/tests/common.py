# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

MOCK_INSTANCES = {
    "NTDS": ["NTDS"],
    "Netlogon": ["_Total"],
    "Security System-Wide Statistics": ["_Total"],
    "DHCP Server": ["_Total"],
    "DFS Replicated Folders": ["InstanceOne", "InstanceTwo"],
}

# This is a complete mock database of all counters the check knows about.
# This prevents the "None of the specified counters are installed" error.
PERFORMANCE_OBJECTS = {
    "NTDS": (
        ["NTDS"],
        {
            'DRA Inbound Bytes Compressed (Between Sites, After Compression)/sec': [9000],
            'DRA Inbound Bytes Compressed (Between Sites, Before Compression)/sec': [9000],
            'DRA Inbound Bytes Not Compressed (Within Site)/sec': [9000],
            'DRA Inbound Bytes Total/sec': [9000],
            'DRA Inbound Full Sync Objects Remaining': [9000],
            'DRA Inbound Objects/sec': [9000],
            'DRA Inbound Objects Applied/sec': [9000],
            'DRA Inbound Objects Filtered/sec': [9000],
            'DRA Inbound Object Updates Remaining in Packet': [9000],
            'DRA Inbound Properties Applied/sec': [9000],
            'DRA Inbound Properties Filtered/sec': [9000],
            'DRA Inbound Properties Total/sec': [9000],
            'DRA Inbound Values (DNs only)/sec': [9000],
            'DRA Inbound Values Total/sec': [9000],
            'DRA Outbound Bytes Compressed (Between Sites, After Compression)/sec': [9000],
            'DRA Outbound Bytes Compressed (Between Sites, Before Compression)/sec': [9000],
            'DRA Outbound Bytes Not Compressed (Within Site)/sec': [9000],
            'DRA Outbound Bytes Total/sec': [9000],
            'DRA Outbound Objects Filtered/sec': [9000],
            'DRA Outbound Objects/sec': [9000],
            'DRA Outbound Properties/sec': [9000],
            'DRA Outbound Values (DNs only)/sec': [9000],
            'DRA Outbound Values Total/sec': [9000],
            'DRA Pending Replication Synchronizations': [9000],
            'DRA Sync Requests Made': [9000],
            'DS Threads in Use': [9000],
            'LDAP Client Sessions': [9000],
            'LDAP Bind Time': [9000],
            'LDAP Successful Binds/sec': [9000],
            'LDAP Searches/sec': [9000],
            'LDAP Writes/sec': [9000],
            'LDAP Active Threads': [9000],
            'DS Client Binds/sec': [9000],
        },
    ),
    "Netlogon": (
        ["lab.local"],
        {
            'Semaphore Waiters': [9000],
            'Semaphore Holders': [9000],
            'Semaphore Acquires': [9000],
            'Semaphore Timeouts': [9000],
            'Average Semaphore Hold Time': [9000],
            'Last Authentication Time': [9000],
        },
    ),
    "Security System-Wide Statistics": (
        ["Security"],
        {
            'NTLM Authentications': [9000],
            'Kerberos Authentications': [9000],
        },
    ),
    "DHCP Server": (
        ["DHCPServer"],
        {
            'Binding Updates Dropped': [9000],
            'Failover: Update pending messages': [9000],
            'Failover: Messages received/sec': [9000],
            'Failover: Messages sent/sec': [9000],
        },
    ),
    "DFS Replicated Folders": (
        ["InstanceOne", "InstanceTwo"],
        {
            'Size of Files Deleted': [9000, 42],
            'Staging Space In Use': [9000, 42],
            'File Installs Retried': [9000, 42],
            'Conflict Folder Size': [9000, 42],
        },
    ),
}
