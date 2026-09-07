# TAXII

## Overview

STIX/TAXII enables you to:

- Pull threat intelligence from any TAXII 2.1 server into Cloud SIEM.
- Poll several collections from one TAXII feed, each on its own schedule.
- Match and enrich your logs with ingested indicators.

### About STIX and TAXII

STIX 2.1 is the standard format for describing threat intelligence: indicators, malware, campaigns, and the relationships between them. TAXII 2.1 is the HTTPS API used to exchange those objects, where a server groups its objects into named collections that clients poll.

Datadog acts as a TAXII client. It authenticates to a server you supply and polls the collections you add by ID, fetching new objects on the interval you choose. Because both are open standards, this one tile covers any vendor or community feed that speaks TAXII 2.1, with no per-vendor integration required.

## Setup

Configuration is managed through the Cloud SIEM interface. For more information, see the [TAXII Configuration UX Requirements](https://datadoghq.atlassian.net/wiki/spaces/CSiem/pages/7117537982/TAXII+Configuration+UX+Requirements).

## Troubleshooting

Contact [Datadog support](mailto:help@datadoghq.com).
