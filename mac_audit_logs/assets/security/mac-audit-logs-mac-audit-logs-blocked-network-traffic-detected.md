## Goal
Identify instances where network traffic is being blocked by the system, potentially indicating security policies in action, unauthorized connection attempts, or misconfigured firewall rules.

## Strategy
Monitor Mac audit logs for blocked network traffic events to detect potential security threats, such as unauthorized outbound connections, intrusion attempts, or unintended service disruptions.

## Triage and response
1. Identify the user `{{@usr.name}}` to determine if the blocked connection originated from a trusted or malicious entity.
2. Check the blocking mechanism to see if it was enforced by macOS firewall, application-layer rules, or third-party security tools.
3. Investigate potential security threats by looking for repeated blocked attempts or correlating with other security logs.
5. Remediate by adjusting firewall rules if necessary, blocking unauthorized sources, updating security policies, and conducting further analysis.