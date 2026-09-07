# TAXII

## Overview

TAXII enables you to:

- Pull threat intelligence from any TAXII 2.1 server into Cloud SIEM.
- Poll several collections from one TAXII feed, each on its own schedule.
- Match and enrich your logs with ingested indicators.

### About STIX and TAXII

STIX 2.1 is the standard format for describing threat intelligence: indicators, malware, campaigns, and the relationships between them. TAXII 2.1 is the HTTPS API used to exchange those objects, where a server groups its objects into named collections that clients poll.

Datadog acts as a TAXII client. It authenticates to a server you supply and polls the collections you add by ID, fetching new objects on the interval you choose. Because both are open standards, this one tile covers any vendor or community feed that speaks TAXII 2.1, with no per-vendor integration required.

## Installation

Click "New" and enter the TAXII server's API root URL and its credentials.

Add each collection you want to ingest by its ID. Objects are mapped to STIX 2.1 and made available to Cloud SIEM detection rules.

## Troubleshooting

Need help? Contact [Datadog support](https://www.datadoghq.com/support/).

### Before you open a ticket

Most TAXII problems are server-side. Include these from the Configure tab so support can reproduce the failure:

- The TAXII feed's API root URL and authentication method (never the credentials themselves).
- The collection ID, if the problem is scoped to one collection.
- The exact status and failure detail shown on the feed or collection row.

### Things to check first

**Feed status is Pending.** Nothing has been contacted yet. A feed is only reached when the next poll of a polling collection runs; add a collection and turn polling on.

**Authentication failed.** The credentials were rejected. Use Update credentials on the feed and wait for the next poll.

**Every collection on a feed is failing.** The feed's status is Error because none of its polling collections succeeded. When they all fail at once, the credentials are the usual cause: use Update credentials on the feed and wait for the next poll.

**Server does not support STIX 2.1.** Datadog only ingests STIX 2.1. TAXII 1.x and STIX 1.x servers are not supported.

**Connection timeout or TLS handshake failed.** Usually a network path or certificate problem on the server side, not something Datadog can retry around.

For questions about the TAXII standard itself rather than this integration, see the [OASIS CTI documentation](https://docs.oasis-open.org/cti/).
