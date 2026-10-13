# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Error code reported by PanosApiError when a response body is not parseable XML.
PARSE_ERROR_CODE = 'parse'

# `code` values PAN-OS uses for a rejected API key. 403 is lab-confirmed; 16 comes from the XML API error-codes doc
# and was never seen in the lab.
AUTH_ERROR_CODES = frozenset({'403', '16'})

# Seconds between two runs of each collector, per firewall. `jobs` and the threat `seqno` reset check are not
# scheduled collectors: the first runs whenever a collector is due, the second lives inside `threats`.
INTERVALS = {
    'bgp': 120,
    'dataplane': 120,
    'interfaces': 180,
    'system_resources': 180,
    'vpn': 180,
    'ha': 180,
    'rule_hits': 180,
    'global_counters': 180,
    'ospf': 180,
    'environment': 300,
    'threats': 300,
    'disk': 1800,
    'identity_metadata': 1800,
    'reports': 1800,
    'licenses': 86400,
}
COLLECTORS = tuple(INTERVALS)

# `device_vendor` tag value (decision 27; the NDM metadata `vendor` is a different string).
DEVICE_VENDOR_TAG = 'paloaltonetworks'
NDM_DEVICE_RESOURCE_TAG = 'dd.internal.resource:ndm_device'
NDM_DEVICE_USER_TAGS_RESOURCE_TAG = 'dd.internal.resource:ndm_device_user_tags'
NDM_INTERFACE_RESOURCE_TAG = 'dd.internal.resource:ndm_interface'

# A firewall is busy, and is not collected, while `show jobs pending` lists a job with one of these statuses and types.
# The type strings are the ones seen in the lab's `show jobs all`; `Downld` (hourly downloads) and `IoT` never pause
# collection.
BUSY_JOB_STATUSES = frozenset({'ACT', 'PEND'})
BUSY_JOB_TYPES = frozenset({'Commit', 'AutoCom', 'Content', 'Antivirus', 'WildFire'})
# After this many seconds of continuously skipping a busy firewall, the check collects it anyway.
COMMIT_SKIP_MAX_SECONDS = 600

# Threat logs: entries asked per `type=log` job (the PAN-OS maximum), how often a job is polled and how long to wait
# between polls before it is left for the next run, and the minimum seconds between two `seqno` reset checks.
THREAT_PAGE_SIZE = 5000
THREAT_JOB_POLLS = 5
THREAT_JOB_POLL_DELAY = 1.0
THREAT_RESET_CHECK_SECONDS = 1800

# NDM metadata values (the `vendor` here differs from the `device_vendor` tag).
NDM_INTEGRATION = 'pan_firewall'
NDM_VENDOR = 'Palo Alto Networks'
NDM_OS_NAME = 'PAN-OS'
NDM_DEVICE_TYPE = 'firewall'
