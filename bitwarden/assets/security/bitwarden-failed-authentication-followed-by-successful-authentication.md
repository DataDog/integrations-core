## Goal
Identify cases where multiple failed authentication attempts are followed by a successful authentication, potentially indicating brute-force attacks, credential stuffing, or unauthorized access attempts.

## Strategy
This rule monitors Bitwarden event logs to trigger an alert on detection of repeated failed authentication attempts by a user, followed by a successful authentication within a short timeframe, to detect potential security threats.

## Triage and Response
1. Review authentication attempts for the user: `{@usr.name}}`, who experienced multiple failed logins followed by a successful one.
2. Contact the user to confirm if they were responsible for the login and if the user denies, escalate for further investigation.
3. Check if failed and successful login attempts originated from a trusted network (VPN, corporate infrastructure) or an unfamiliar/suspicious external IP.
4. Check for related indicators like 2FA disablement, device approvals, or account recovery events in the same timeframe.
5. Analyze the time gap between failed attempts and successful login to assess if it indicates brute-force activity.
6. Reset user credentials if compromise is suspected.
7. Escalate to the security team if malicious intent is observed, following the incident response plan.