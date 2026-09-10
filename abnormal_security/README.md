## Overview

Abnormal Security provides comprehensive email protection using a platform that understands human behavior. It protects against attacks that exploit human behavior, including phishing, social engineering, and account takeovers.

Datadog's integration with Abnormal Security collects logs using [Abnormal Security's API][3], which generates three types of logs:

- **Threat Logs**: Threat logs include any malicious activity or attack that could harm an organization, its data, or personnel.
- **Case Logs**: Case logs include Abnormal Cases that are identified by Abnormal Security. These cases usually include related threats within them. **Note:** The Account Takeover product is required to collect Case Logs.
- **Audit Logs**: These logs include actions taken on the Abnormal portal.

## Setup

### Configuration

1. Sign into your [Abnormal Security Account][2].
2. Click **Abnormal REST API**.
3. Retrieve your authentication token on the Abnormal portal and input it in the account table.

This token is used to view your Abnormal detected threats, cases, and audit logs.

### Validation

1. Ensure you have a log index configured for `source:abnormal-security` in your Datadog account.
2. After configuration, logs should appear in the [Log Explorer][4] within 5 minutes. You can access the Log Explorer directly from the **Data Collected** tab of the Abnormal Security integration tile.
3. Filter logs by `source:abnormal-security` to view your Abnormal Security threat, case, and audit logs.
4. If utilizing this integration with our [Cloud SIEM][6] product, we recommend complementing with our [Abnormal Security Content Pack][5].

## Data Collected

### Metrics

The Abnormal Security integration does not include any metrics.

### Log Collection

Abnormal Security Incidents, Cases, and Audit logs will show up under the source `abnormal-security`.

### Events

The Abnormal Security integration does not include any events.

### Service Checks

The Abnormal Security integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][1].

[1]: https://docs.datadoghq.com/help/
[2]: https://portal.abnormalsecurity.com/home/settings/integrations
[3]: https://app.swaggerhub.com/apis/abnormal-security/abx/1.4.3#/info
[4]: https://docs.datadoghq.com/logs/explorer/
[5]: https://docs.datadoghq.com/security/cloud_siem/content_packs/#email_security
[6]: https://www.datadoghq.com/product/cloud-siem/
