## Goal
Identify incidents where the same security policy or event type, particularly those categorized as high risk, is triggered across multiple hosts within the network. This pattern may indicate a coordinated attack, a widespread vulnerability, or a configuration issue that could compromise multiple endpoints.

## Strategy
Monitor behavior monitoring events for instances where the same high-risk policy type or event type is detected on multiple hosts. Correlate these events to assess the potential threat, identify common factors or entry points, and prioritize remediation efforts to mitigate the risk across the affected endpoints.

## Triage and Response
1.  Identify the affected hosts, including their host names - `{{source_host_name}}`.
2.  Verify the specific policy type (`{{@policy_type}}`) and event type (`{{event_type}}`) that triggered the signal.
3.  Determine whether the detected issue represents a known vulnerability, misconfiguration, or a targeted attack.
4.  Assess the scope of the issue by identifying all endpoints affected.
5.  Implement corrective actions such as adjusting policies, patching vulnerabilities, or isolating compromised hosts to prevent further impact.