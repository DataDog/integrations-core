## Goal
Identify new incidents reported by Palo Alto Networks Cortex XSOAR to detect potential threats.

## Strategy
This rule monitors new incidents reported by Palo Alto Networks Cortex XSOAR, allowing security teams to promptly investigate and respond to emerging threats identified.

## Triage and Response
- Review the incident details and severity level to assess potential impact.
- Review incident type `{{@type}}` and source instance `{{@sourceInstance}}` to understand the origin.
- Verify the incident status to confirm whether it is still being investigated.
- Review the assignee to identify the owner responsible for investigation and examine the associated playbook to confirm automated response execution.
- If the incident is still Active, take appropriate remediation actions based on the incident type and severity, such as isolating systems, running scans, or applying patches.
- Notify the relevant security teams with incident details and severity classification to coordinate response and mitigation efforts.