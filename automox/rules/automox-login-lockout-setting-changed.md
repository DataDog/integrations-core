## Goal
Detect a change to an Automox zone's login-attempt lockout setting.

## Strategy
This rule fires on the audit event `Zone Login Attempts Setting Changed` (`@ocsf.class_uid:3004`). Raising the allowed attempts or lengthening the decay weakens the brute-force protection on console sign-in. The new limits stay inside `raw_data`, so the rule cannot by itself tell loosening from tightening; it flags the change for review. The signal is grouped by the zone (`@ocsf.entity.uid`).

## Triage and response
- Review the new lockout values to determine whether the change loosened the control.
- Confirm whether an approved policy change explains it.
- Attribute the change to a console session via the preceding authentication events.
- Check for login failures against the zone after the change.
- If unexplained, restore the prior lockout setting.
