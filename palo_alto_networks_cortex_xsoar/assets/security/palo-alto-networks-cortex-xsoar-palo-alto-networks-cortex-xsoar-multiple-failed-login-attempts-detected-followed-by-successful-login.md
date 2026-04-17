## Goal
Identify cases where a user experiences multiple failed login attempts followed by a successful login, potentially indicating a brute-force attack, credential stuffing, or unauthorized access.

## Strategy
This rule monitors failed login attempts and detects cases where a user successfully logs in after several failures. This pattern may indicate that an attacker has successfully guessed or obtained valid credentials.

## Triage and Response
- Identify the user `{{@usr.name}}` associated with the failed login attempts followed by a successful login.
- Investigate if there are any ongoing system issues or maintenance activities that could account for increased login failures.
- If suspicious behavior is detected, consider locking the affected accounts, notifying users, and requiring additional authentication steps.