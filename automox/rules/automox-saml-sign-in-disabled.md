## Goal
Detect SAML single sign-on being disabled for an Automox zone.

## Strategy
This rule fires on the audit event `Zone SAML Disabled` (`@ocsf.class_uid:3004`). Disabling SAML turns off the organization's single sign-on and the central controls behind it (MFA policy, conditional access and deprovisioning) and falls back to local Automox passwords. The signal is grouped by the zone (`@ocsf.entity.uid`).

## Triage and response
- Confirm whether an approved change to the identity configuration explains it.
- Review authentication events after the change for local-password sign-ins that bypass SSO.
- Determine whether local accounts were created around the same time.
- Attribute the change to a console session via the preceding authentication events.
- If unexplained, re-enable SAML and review accounts that signed in while it was off.
