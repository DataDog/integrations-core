## Goal
Detect activity observed from a potential malicious IP address.

## Strategy
Monitor Bitwarden event logs and detect activity from potentially malicious IP addresses. Datadog enriches all ingested logs with expert-curated threat intelligence in real-time.

## Triage and response
1. Determine if the user: `{{@usr.name}}` from IP address: `{{@network.client.ip}}` should have performed activity: `{{@evt.name}}`.
2. Investigate the user's recent activity and login history to identify potential anomalies.
3. If the activity is deemed suspicious, temporarily revoke the user's access and consider escalating the incident to the security team for further investigation and potential remediation.