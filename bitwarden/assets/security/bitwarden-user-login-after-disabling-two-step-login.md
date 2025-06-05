## Goal
Detect a user login after two-step login (2FA) has been deactivated.

## Strategy
This rule monitors Bitwarden event logs to identify user logins that occur after two-step login has been disabled. Such behavior may indicate a reduction in account security and could point to a compromised account or potential insider threat.

## Triage and response
1.  Confirm whether the user: `{{@usr.name}}` intentionally disabled two-step login.
2.  If the user denies the action or cannot be contacted, treat the activity as suspicious and investigate further.
3.  Investigate associated IPs for unfamiliar or suspicious geolocations.
4.  Look for signs of account takeover (e.g., password resets, vault exports).
5.  If the action was unauthorized, force re-enrollment in 2FA.
6.  Remove user's access if compromise is suspected and reset credentials.
7.  Notify the security team and monitor the user for ongoing anomalous behavior.