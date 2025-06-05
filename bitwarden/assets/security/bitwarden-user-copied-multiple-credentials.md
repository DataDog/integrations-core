## Goal
Detect password copy attempts more than the defined threshold from Bitwarden Vault.

## Strategy
This rule monitors Bitwarden event logs and triggers an alert when multiple credentials are copied by a user.

## Triage & response
1. Investigate the user `{{@usr.name}}` attempting to copy credentials.
2. If this action was unintended by the user:
    - Temporarily revoke the user’s access.
    - Rotate the user's Bitwarden master password.
    - Identify all the items within the vault that were copied and rotate the necessary credentials.