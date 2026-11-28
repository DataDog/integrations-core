## Goal
Detect Automox agent auto-update being switched off for a zone.

## Strategy
This rule fires on the audit event `Agent Auto Update Switched From On to Off` (`@ocsf.class_uid:6001`). With auto-update off, agents stop upgrading themselves and can fall behind on fixes, which weakens the patch posture the agent exists to maintain. The signal is grouped by the zone (`@ocsf.web_resources.uid`).

## Triage and response
- Confirm whether a staged rollout or a compatibility concern explains disabling auto-update.
- Determine how many devices the zone covers.
- Attribute the change to a console session via the preceding authentication events.
- Check whether other defensive settings were changed in the same period.
- If unexplained, re-enable auto-update.
