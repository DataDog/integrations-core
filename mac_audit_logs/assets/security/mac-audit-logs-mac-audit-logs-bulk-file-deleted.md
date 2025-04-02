## Goal
Detect instances where a large number of files are deleted in a short timeframe, which may indicate unauthorized data removal, malicious activity, or system misconfiguration.

## Strategy
Monitor Mac audit logs for bulk file deletion events to identify potential security risks, such as data destruction, malware activity, insider threats, or automated script executions.

## Triage and response
1. Identify the user `{{@usr.name}}` responsible for the bulk file deletions and verify if it aligns with normal operations.
2. Determine the file paths `{{@record.path}}`, sensitivity of the deleted files to assess potential data loss impact.
3. Correlate with other security logs to identify related security events, such as unauthorized access attempts or anomalies in file system activity.
4. Remediate by restoring critical files if necessary, restricting bulk deletion permissions, and reviewing security policies for further mitigation.