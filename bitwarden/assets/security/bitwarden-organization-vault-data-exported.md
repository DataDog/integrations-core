## Goal
Detect when an organization vault's data is exported by a user.

## Strategy
Monitor Bitwarden event logs to detect vault export activities initiated by a user, as these actions may indicate data exfiltration or a potential insider threat.

## Triage and response
1. Confirm that the export action was performed by the user: `{{@usr.name}}`. Contact the user directly to verify the intent and legitimacy.
2. If the user denies the action or cannot be contacted, treat the activity as suspicious and investigate further.
3. Check if the associated IP addresses are unfamiliar or deviate from the user's typical login patterns (e.g., unusual locations or signs of impossible travel).
4. If the export is deemed suspicious, immediately revoke access for the user.
5. Reset the master password if the user's account compromise is suspected.
6. Audit the content of the exported data to identify any sensitive credentials or vault items that could pose further risk.
7. Implement security measures such as rotating exposed secrets, enforcing two-factor authentication, and notifying administrators and the security team about the potential breach.