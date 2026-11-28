## Goal
Detect a successful Automox console sign-in after repeated failures for the same user, a possible password-guessing success.

## Strategy
This rule counts `User Log In Failure` and `User Log In Success` authentication events (`@ocsf.class_uid:3002`) for the same account (`@ocsf.user.email_addr`) in a 15-minute window, and fires when more than five failures are followed by a success. Login failures carry no `user.uid`, so the email address is the correlation key. Automox records no source IP, so this count-based heuristic stands in for an impossible-travel or new-location rule.

## Triage and response
- Confirm whether the user was resetting a password or mistyping, which produces the same pattern.
- Review what the account did after signing in: API key creation, policy creation or on-demand runs.
- Determine whether the account holds elevated roles.
- Check for the same pattern across other accounts in the same window.
- If unexplained, reset the account's credentials and review its recent console actions.
