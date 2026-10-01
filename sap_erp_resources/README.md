# SAP S/4HANA Sales Orders

## Overview

This integration reads sales orders from SAP S/4HANA (private cloud or on-premise) through the released OData V4 `API_SALESORDER` service and stores them in Datadog as resources: sales-order headers, items, and schedule lines, with per-order and per-run coverage records. Access is read-only. Amounts and quantities are kept exactly as SAP returns them.

## Setup

### Installation

No Datadog Agent installation is required. Datadog connects to the SAP system over HTTPS.

### Configuration

In SAP, with an administrator user:

1. **Technical user:** create or reuse a dedicated, read-only user of type *System* (`SU01`).
2. **Publish the service:** in `/IWFND/V4_ADMIN`, choose *Publish Service Groups*, select the local system alias, and publish `API_SALESORDER`.
3. **Authorize the service:** in `PFCG`, add the authorization default `R3TR G4BA API_SALESORDER` to the user's role, together with display access (activity `03`) to sales documents for the sales organizations to collect (`V_VBAK_VKO`). Generate the profile and run the user comparison.
4. **Network:** make the service reachable from Datadog over HTTPS, following your organization's exposure policy. Keep proxy URL limits of at least 2 KB.

In Datadog, add an account with:

- the service root URL, SAP system number, SAP client, and the sales organizations to collect;
- the technical user and password.

The SAP system number and client identify the collected data and cannot be changed later.

### Validation

`GET <service root>$metadata` and `GET <service root>SalesOrder?$top=1` must both return HTTP 200 for the technical user.

| Response | Cause |
|---|---|
| 401 | Wrong password or locked user |
| 404 `/IWBEP/CM_V4_COS/014` | Service group not published (step 2) |
| 403 `/IWBEP/CM_V4_COS/011` | Service group not authorized (step 3) |

## Data Collected

### Metrics

SAP S/4HANA Sales Orders does not include any metrics.

### Events

SAP S/4HANA Sales Orders does not include any events.

### Service Checks

SAP S/4HANA Sales Orders does not include any service checks.

## Support

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
