## Goal
Detect an organization-wide installation of the Splashtop remote-control streamer across the Automox fleet.

## Strategy
This rule fires on the audit event `Org-Wide Splashtop Streamer Install Initiated` (`@ocsf.class_uid:6001`), which Automox records when an administrator pushes the Splashtop streamer to every device in the organization at once. Installing remote-access software fleet-wide gives an operator interactive control of every managed endpoint. Automox records no actor on Splashtop events, so the signal follows the organization resource in `@ocsf.web_resources.uid`.

## Triage and response
- Confirm whether a remote-support rollout or an approved change explains the org-wide install.
- Review Automox authentication events just before the install to attribute it to a console session.
- Look for `Splashtop Connection Initiated` events afterwards, which indicate the streamer was used.
- Determine whether remote-control consent was weakened in the same period (`Splashtop Bulk Remote Control Consent Changed`).
- If unexplained, reverse the streamer deployment and review who can change remote-control settings.
