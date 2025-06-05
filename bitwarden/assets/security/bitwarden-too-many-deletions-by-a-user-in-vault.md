## Goal
Detect when a user performs a high number of data deletion activities in the organization vault.

## Strategy
This rule monitors Bitwarden event logs and triggers an alert upon detecting a high volume of data deletion activity by a user in the organization vault, which may indicate malicious behavior or account compromise.

## Triage and response
1.  Confirm if the deletions by user: `{{@usr.name}}` were intentional and approved.
2.  Check recent user activity such as vault export, password changes, or new device logins.
3.  Identify if the associated IP addresses are unfamiliar or from a suspicious location.
4.  Revoke access if the activity is unapproved or suspicious.
5.  Assess the impact by identifying the nature of the deleted credentials.
6.  Notify the security team immediately to initiate incident response procedures.