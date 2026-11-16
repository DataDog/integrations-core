## Goal
Detect a local Automox user being created in an organization that also provisions users through SAML.

## Strategy
This rule runs two `/events` queries for the same organization (`@organization_id`) within 24 hours: `@evt.name:user.create` (a local account) and `@evt.name:saml.user.create` (an SSO account). Both map to OCSF Account Change (3001), so the raw event name is what tells them apart. A SAML sign-up shows the organization uses SSO; a local account created in the same period sidesteps it, which is how an operator keeps a password-based account alongside the federated ones. The two can appear in either order.

The evaluation window is 24 hours, the longest a Cloud SIEM threshold rule allows. A settled SSO organization creates SAML users only as new people first sign in, so this rule can miss a local account created more than a day from the nearest SAML sign-up. A longer, 7-to-30-day window needs a scheduled SQL rule over the `ocsf_account_change` dataset, which can still split the two events by `@ocsf.metadata.event_code`; that becomes workable once Automox console events carry the organization in OCSF, so the rule can keep grouping by organization (`@ocsf.user.org.uid`).

## Triage and response
- Identify the local account and who created it.
- Confirm whether a break-glass or service account justifies a local credential.
- Determine whether the local account holds elevated roles.
- Review whether SAML sign-in was disabled around the same time.
- If unexplained, remove or federate the local account and review its activity.
