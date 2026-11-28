## Goal
Detect a remote-control session opened to a device shortly after its consent requirement was removed.

## Strategy
This rule correlates two audit events on the same device (`@ocsf.web_resources.uid`): first `Splashtop Remote Control Consent Changed` to an unattended or no-consent setting (`@ocsf.unmapped.new_consent_required:false` or `@ocsf.unmapped.new_access_type:(unattended OR attended_allow_on_timeout)`), then a `Splashtop Connection Initiated` within a day. Removing consent and then connecting is the sequence an operator follows to reach an endpoint without the user approving the session. Splashtop events name no actor, so the correlation follows the device.

## Triage and response
- Confirm whether an approved remote-support session explains the connection.
- Identify the device, and the operator if an authentication event around the connection attributes it.
- Determine what happened during the session: policy runs, worklet executions or patch actions on that device.
- Check whether consent was restored afterwards or left disabled.
- If unexplained, restore consent and investigate the device's activity during the session window.
