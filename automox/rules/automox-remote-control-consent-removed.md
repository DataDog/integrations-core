## Goal
Detect remote-control consent being weakened across many Automox devices at once.

## Strategy
This rule fires on the audit event `Splashtop Bulk Remote Control Consent Changed` (`@ocsf.class_uid:6001`) when the new setting removes the end-user consent prompt (`@ocsf.unmapped.new_consent_required:false`) or switches access to an unattended mode (`@ocsf.unmapped.new_access_type:(unattended OR attended_allow_on_timeout)`). The bulk event applies the change to many devices at once, so an operator can reach them over Splashtop with no user present to approve the session. Splashtop events name no actor, so the signal follows the organization resource in `@ocsf.web_resources.uid`.

## Triage and response
- Confirm whether an approved remote-support configuration explains the move to unattended access.
- Identify how many devices were affected (`@ocsf.unmapped.device_count`).
- Review authentication events preceding the change to attribute it to a console session.
- Look for `Splashtop Connection Initiated` events to those devices afterwards.
- If unexplained, restore the consent requirement and review who can change remote-control settings.
