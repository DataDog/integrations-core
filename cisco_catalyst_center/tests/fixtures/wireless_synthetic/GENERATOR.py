# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Regenerate the synthetic access point and controller payload.

Run from this directory: ``python GENERATOR.py``

Why this exists as a script rather than a hand-edited JSON file: the field *names* must come
from Cisco's schema, not from a developer's memory of it, and a reviewer needs to be able to
tell which parts were observed and which were invented.

Construction:

* Every key outside ``apDetails`` is copied from a real captured switch record, so the common
  device shape matches what the appliance actually returns rather than what the spec claims.
  The two differ -- the runtime record carries ``reachabilityHealthStatus``, which the spec
  omits, and the spec names a ``macAddr`` interface field that runtime does not return.
* ``apDetails`` and its nested ``radios`` come from ``ApConfigurationDetails`` and ``RadioKpi``
  in ``CE_Cat_Center_Org-AssuranceNetworkDevices-1.0.2-resolved.yaml``.

Values are hand-chosen to be physically plausible. Cisco's schema examples are not: the example
for ``RadioKpi.noise`` is ``10`` on a field documented in dBm, where a real 5 GHz noise floor is
near -95. Distinct values are used per radio and per field so that a swapped tag mapping fails a
test instead of passing on coincidentally equal numbers.

NO VALUE HERE HAS BEEN OBSERVED ON A REAL CONTROLLER. Replace this file wholesale with a real
capture during a reserved-sandbox window; do not incrementally "correct" it.
"""

from __future__ import annotations

import json
from pathlib import Path

CAPTURED = Path(__file__).resolve().parents[1] / 'captured' / 'data_network_devices.json'
OUT = Path(__file__).parent / 'data_network_devices_wireless.json'

# ApConfigurationDetails, 27 properties. Order preserved from the schema.
AP_DETAILS_TEMPLATE = {
    'connectedWlcName': 'wlc1.example.com',
    'policyTagName': 'campus-policy-tag',
    'apOperationalState': 'Registered',
    'powerSaveMode': 'Disabled',
    'operationalMode': 'Local',
    'resetReason': 'Power over Ethernet',
    'protocol': '11AX',
    'powerMode': 'FULL_POWER',
    'connectedTime': 1754300000,
    'ledFlashEnabled': False,
    'ledFlashSeconds': 0,
    'subMode': 'Local',
    'homeApEnabled': False,
    'powerType': 'PoE',
    'apType': 'Standard',
    'adminState': 'AP_ADMIN_STATE_ENABLED',
    'icapCapability': '159',
    'regulatoryDomain': 'US  - United States',
    'ethernetMac': '68:7D:B4:1C:0B:24',
    'rfTagName': 'campus-rf-tag',
    'siteTagName': 'campus-site-tag',
    'powerSaveModeCapable': 'AP_POWER_SAVE_MODE_CAPABLE_SUPPORTED',
    'powerProfile': 'default-power-profile',
    'flexGroup': None,
    'powerCalendarProfile': None,
    'apGroup': 'campus-floor-2',
    'radios': [],
}

# RadioKpi, 8 properties. noise is dBm; airQuality, interference, trafficUtil and utilization
# are percentages; clientCount is a count.
RADIOS = [
    {
        'slot': '0',
        'radioBand': '2.4Ghz',
        'noise': -92,
        'airQuality': 87,
        'interference': 12,
        'trafficUtil': 23,
        'utilization': 35,
        'clientCount': 7,
    },
    {
        'slot': '1',
        'radioBand': '5Ghz',
        'noise': -97,
        'airQuality': 94,
        'interference': 3,
        'trafficUtil': 29,
        'utilization': 41,
        'clientCount': 13,
    },
]


def _blank_like(record: dict) -> dict:
    """Copy a captured record's key set, clearing values that are switch-specific."""
    return dict.fromkeys(record)


def build() -> dict:
    captured = json.loads(CAPTURED.read_text())
    switch = captured['response'][0]

    ap = _blank_like(switch)
    ap.update(
        {
            'id': 'a1b2c3d4-0000-4000-8000-00000000ap01',
            'name': 'ap-floor2-01',
            'managementIpAddress': '10.20.30.41',
            'deviceFamily': 'Unified AP',
            'deviceType': 'Cisco Catalyst 9130AXI Unified Access Point',
            'deviceSeries': 'Cisco Catalyst 9130 Series Unified Access Points',
            'deviceRole': 'ACCESS',
            'platformId': 'C9130AXI-B',
            'serialNumber': 'FGL2725L0AP',
            'macAddress': '68:7d:b4:1c:0b:20',
            'osType': 'IOS-XE',
            'softwareVersion': '17.12.1prd9',
            'productVendor': 'Cisco',
            'reachabilityHealthStatus': 'REACHABLE',
            'communicationState': 'REACHABLE',
            'collectionStatus': 'SUCCESS',
            'siteHierarchy': 'Global/US/Campus/Building-1/Floor-2',
            'siteHierarchyId': '/uuid-global/uuid-us/uuid-campus/uuid-b1/uuid-f2',
            'siteId': 'uuid-f2',
            'clientCount': 20,
            'wirelessClientCount': 20,
            'wiredClientCount': 0,
            'upTime': 864000,
            'apDetails': {**AP_DETAILS_TEMPLATE, 'radios': RADIOS},
            'metricsDetails': {
                **dict.fromkeys(switch['metricsDetails']),
                'overallHealthScore': 9,
                'noiseScore': 8,
                'utilizationScore': 6,
                'interferenceScore': 10,
                'airQualityScore': 9,
                'cpuUtilization': 17.5,
                'cpuScore': 10,
                'memoryUtilization': 43.2,
                'memoryScore': 9,
            },
        }
    )

    wlc = _blank_like(switch)
    wlc.update(
        {
            'id': 'a1b2c3d4-0000-4000-8000-0000000wlc01',
            'name': 'wlc1.example.com',
            'managementIpAddress': '10.20.30.10',
            'deviceFamily': 'Wireless Controller',
            'deviceType': 'Cisco Catalyst 9800-CL Wireless Controller for Cloud',
            'deviceSeries': 'Cisco Catalyst 9800 Series Wireless Controllers',
            'deviceRole': 'ACCESS',
            'platformId': 'C9800-CL-K9',
            'serialNumber': 'TTM254900WL',
            'macAddress': '00:1e:bd:00:00:10',
            'osType': 'IOS-XE',
            'softwareVersion': '17.12.1prd9',
            'productVendor': 'Cisco',
            'reachabilityHealthStatus': 'REACHABLE',
            'communicationState': 'REACHABLE',
            'collectionStatus': 'SUCCESS',
            'siteHierarchy': 'Global/US/Campus',
            'siteHierarchyId': '/uuid-global/uuid-us/uuid-campus',
            'siteId': 'uuid-campus',
            'clientCount': 20,
            'wirelessClientCount': 20,
            'wiredClientCount': 0,
            'upTime': 1728000,
            # A controller reports no apDetails of its own; it reports how many APs it carries.
            'apDetails': None,
            'metricsDetails': {
                **dict.fromkeys(switch['metricsDetails']),
                'overallHealthScore': 10,
                'apCount': 31,
                'cpuUtilization': 22.9,
                'cpuScore': 10,
                'memoryUtilization': 61.4,
                'memoryScore': 8,
                'freeTimer': 99.93,
                'freeTimerScore': 10,
                'packetPool': 409428,
                'packetPoolScore': 10,
                'freeMemoryBuffer': 38.6,
                'freeMemoryBufferScore': 9,
                'wqePool': 409503,
                'wqePoolScore': 10,
            },
        }
    )

    return {'version': '1.0', 'response': [ap, wlc], 'page': {'limit': 500, 'offset': 1, 'count': 2}}


if __name__ == '__main__':
    OUT.write_text(json.dumps(build(), indent=2, sort_keys=True) + '\n')
    print(f'wrote {OUT}')
