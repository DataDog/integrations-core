# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Endpoint paths and the per-endpoint facts a caller must not have to remember."""

from __future__ import annotations

from typing import Final

AUTH_ENDPOINT: Final = '/dna/system/api/v1/auth/token'

# Assurance data API: bulk, org-level, paginated.
NETWORK_DEVICES_ENDPOINT: Final = '/dna/data/api/v1/networkDevices'
INTERFACES_ENDPOINT: Final = '/dna/data/api/v1/interfaces'
CLIENTS_ENDPOINT: Final = '/dna/data/api/v1/clients'
CLIENTS_SUMMARY_ANALYTICS_ENDPOINT: Final = '/dna/data/api/v1/clients/summaryAnalytics'
SITE_HEALTH_SUMMARIES_ENDPOINT: Final = '/dna/data/api/v1/siteHealthSummaries'
ASSURANCE_EVENTS_ENDPOINT: Final = '/dna/data/api/v1/assuranceEvents'
ASSURANCE_ISSUES_ENDPOINT: Final = '/dna/data/api/v1/assuranceIssues'

# Intent API: used only where the data API has no equivalent.
NETWORK_APPLICATIONS_ENDPOINT: Final = '/dna/data/api/v1/networkApplications'
FABRIC_SITE_HEALTH_ENDPOINT: Final = '/dna/data/api/v1/fabricSiteHealthSummaries'
VIRTUAL_NETWORK_HEALTH_ENDPOINT: Final = '/dna/data/api/v1/virtualNetworkHealthSummaries'

PHYSICAL_TOPOLOGY_ENDPOINT: Final = '/dna/intent/api/v1/topology/physical-topology'
SITE_TOPOLOGY_ENDPOINT: Final = '/dna/intent/api/v1/topology/site-topology'
L3_TOPOLOGY_ENDPOINT_TEMPLATE: Final = '/dna/intent/api/v1/topology/l3/{topology_type}'
SECURITY_ROGUE_ENDPOINT: Final = '/dna/intent/api/v1/security/rogue/additional/details'
SECURITY_THREATS_ENDPOINT: Final = '/dna/intent/api/v1/security/threats/details'

DEVICE_HEALTH_ENDPOINT: Final = '/dna/intent/api/v1/device-health'
STACK_ENDPOINT_TEMPLATE: Final = '/dna/intent/api/v1/network-device/{device_id}/stack'
NETWORK_HEALTH_ENDPOINT: Final = '/dna/intent/api/v1/network-health'
CLIENT_HEALTH_ENDPOINT: Final = '/dna/intent/api/v1/client-health'
RELEASE_ENDPOINT: Final = '/dna/intent/api/v1/dnac-release'

TOKEN_LIFETIME_SECONDS: Final = 3600

# The cap is not uniform, and exceeding it fails the whole call rather than clamping:
# networkDevices and interfaces answer `2511 Limit can't be more than 500`, siteHealthSummaries
# answers `2005 Value must be in the range 1-20`, assuranceEvents answers `14007`. Measured
# against the DevNet sandbox on 2026-08-05.
DEFAULT_PAGE_LIMIT: Final = 500
ENDPOINT_PAGE_LIMITS: Final[dict[str, int]] = {
    NETWORK_DEVICES_ENDPOINT: 500,
    INTERFACES_ENDPOINT: 500,
    CLIENTS_ENDPOINT: 500,
    SITE_HEALTH_SUMMARIES_ENDPOINT: 20,
    ASSURANCE_EVENTS_ENDPOINT: 20,
    # Measured live: each of these rejects the 500 default with its own ceiling, and the ceilings
    # are all different. There is no pattern to infer -- every new list endpoint has to be probed.
    ASSURANCE_ISSUES_ENDPOINT: 25,
    VIRTUAL_NETWORK_HEALTH_ENDPOINT: 100,
    FABRIC_SITE_HEALTH_ENDPOINT: 100,
    NETWORK_APPLICATIONS_ENDPOINT: 100,
}

# Catalyst Center rejects offset=0 with `2511 Offset can't be less than 1`.
FIRST_OFFSET: Final = 1

# Device families that can be part of a switch stack. Used to bound the per-device stack
# fan-out, which is the only fan-out in the P0 set.
STACKABLE_DEVICE_FAMILIES: Final[frozenset[str]] = frozenset({'Switches and Hubs'})

# `state` values reported for a stack member and a stack port respectively.
STACK_MEMBER_READY_STATES: Final[frozenset[str]] = frozenset({'READY'})
STACK_PORT_OK_VALUES: Final[frozenset[str]] = frozenset({'Yes', 'yes', 'true', 'True'})

# Values the data API reports for a reachable device. The legacy endpoint answers in title
# case (`Reachable`) while the data API answers in upper case, so both are accepted.
DEVICE_REACHABLE_VALUES: Final[frozenset[str]] = frozenset({'REACHABLE', 'Reachable', 'reachable'})

# L3 topology types the brief names.
L3_TOPOLOGY_TYPES: Final[tuple[str, ...]] = ('ospf', 'isis', 'static')

# Values Catalyst Center uses for a topology link that is up.
TOPOLOGY_LINK_UP_VALUES: Final[frozenset[str]] = frozenset({'up', 'UP', 'Up'})

# `fabricRole` is a list whose casing is inconsistent -- the schema example is
# `['Border', 'edge']`, mixing both -- so roles are lower-cased before being tagged.
FABRIC_ROLE_ENDPOINTS_PAGE_LIMIT: Final = 20

# Keys that make up an error object. Used to tell an error apart from a real record, since both
# arrive in the `response` slot.
ERROR_OBJECT_KEYS: Final = frozenset({'detail', 'errorCode', 'message'})
