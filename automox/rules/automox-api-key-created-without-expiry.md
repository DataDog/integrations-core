## Goal
Detect an Automox API key created with no expiry date.

## Strategy
This rule fires on the audit event `API Key Created` (`@ocsf.class_uid:3004`, `@ocsf.entity.type:"API Key"`) where the key carries no expiry (`-@ocsf.entity.data.expires_at:*`). A key with no expiry is a long-lived credential to the Automox API, which can run policies and manage devices, and it never lapses on its own. The signal is grouped by the key (`@ocsf.entity.uid`).

## Triage and response
- Identify the key and whether an approved integration required a new credential.
- Determine whether the key could instead carry an expiry.
- Attribute the creation to a console session via the preceding authentication events.
- Review what the key is used for and whether it holds broad scope.
- If unexplained, disable the key and reissue one with an expiry.
