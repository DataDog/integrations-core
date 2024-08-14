## Goal

Detect events related to content violations as identified by Trend Micro Vision One Endpoint Security. These events may indicate breaches of security policies, such as the inappropriate access to or transmission of sensitive or confidential information, which could pose significant security risks and necessitate immediate attention.

## Strategy

Monitor endpoint security events for indications of content violations. Focus on analyzing the context of the event, including the specific policy settings that were breached and the affected endpoints.

## Triage and Response

1.  Confirm the policy settings associated with the content violation - `{{@policy_settings}}`.
2.  Review the event details to understand the nature of the violation.
3.  Examine the impacted endpoint using its name - `{{source_host_name}}` and IP address - `{{endpoint_ip}}`.
4.  If the content violation is confirmed as a security issue, take appropriate actions to address the breach, such as adjusting policies or restricting access.
5.  Continue to monitor the affected endpoints for further content violations or related anomalies.
