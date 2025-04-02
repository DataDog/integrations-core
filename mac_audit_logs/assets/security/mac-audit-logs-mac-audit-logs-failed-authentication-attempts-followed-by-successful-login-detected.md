## Goal
Identify cases where multiple failed authentication attempts are followed by a successful login, potentially indicating brute-force attacks, credential stuffing, or unauthorized access attempts.

## Strategy
Monitor Mac audit logs for repeated failed authentication attempts on an account, followed by a successful login within a short timeframe, to detect potential security threats.

## Triage and response
1. Identify the user `{{@usr.name}}` that experienced multiple failed authentication attempts and later logged in successfully.
2. Analyze the time gap between failed attempts and successful login to assess if it indicates brute-force activity.
3. Correlate with system logs for additional suspicious activity, such as privilege escalation or access to sensitive files.
4. Remediate by verifying user intent, enforcing multi-factor authentication (MFA), blocking suspicious IPs, and reviewing account security policies.