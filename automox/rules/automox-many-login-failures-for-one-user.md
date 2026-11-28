## Goal
Detect repeated Automox console sign-in failures for a single account.

## Strategy
This rule counts `User Log In Failure` authentication events (`@ocsf.class_uid:3002`) for the same account (`@ocsf.user.email_addr`) and fires at ten or more in 15 minutes, with or without a success. Automox records no source IP and marks no lockout, so the count is the only signal of guessing. It is a lower-severity companion to the failures-then-success rule.

## Triage and response
- Confirm whether a saved or expired credential explains repeated automated failures.
- Determine whether a success followed, which raises the concern.
- Check whether the same source is failing against other accounts.
- Review whether the account is privileged.
- If unexplained, reset the account's credentials.
