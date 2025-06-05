## Goal
Detect and alert when a user purges the organization vault.

## Strategy
This rule monitors Bitwarden event logs and triggers an alert upon detecting a vault purge event. Purging may result in permanent data loss and could indicate malicious activity or account compromise.

## Triage and response
1. Confirm whether the purge was performed by the user: `{{@usr.name}}`. Contact the user to verify intent and legitimacy.
2. If the user denies the action or is unreachable, treat the event as potentially malicious.
3. Review event logs for prior actions such as data access, exports, or credential changes.
4. Investigate the associated IP addresses for signs of: Unfamiliar geolocation, Impossible travel.
5. If compromise is suspected, immediately revoke the user's access and begin incident containment procedures.
6. Notify the security team and begin forensic analysis to assess the scope of data loss and potential impacts.