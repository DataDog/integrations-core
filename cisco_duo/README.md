## Overview

[Cisco Duo][1] is a multi-factor authentication (MFA) and secure access solution. It adds an additional layer of security by requiring users to verify their identity through a second factor, such as a mobile app, before gaining access to applications or systems. Duo is often used to enhance the security of remote access and helps protect against unauthorized access, even if passwords are compromised.

This integration ingests the following logs:
- Authentication
- Activity
- Administrator
- Telephony
- Offline Enrollment

The Cisco Duo integration seamlessly collects multi-factor authentication (MFA) and secure access logs, channeling them into Datadog for analysis. Leveraging the built-in logs pipeline, these logs are parsed and enriched, enabling effortless search and analysis. The integration provides insight into fraud authentication events, authentication activity timeline, locations of accessed, authentication devices, and many more through the out-of-the-box dashboards.

## Setup

### Configuration

#### Get API Credentials of Cisco Duo

1. Sign up for a [**Duo account**][2].
2. Log in to the [**Duo Admin Panel**][3].
3. Navigate to **Applications**.
4. Click **Protect an Application** and locate the entry for _Auth API_ in the applications list.
5. Click **Protect** to the far-right to configure the application and get your `integration key`, `secret key`, and `API hostname`. This information will be used during next step to configure Cisco Duo integration.

#### Cisco Duo DataDog Integration Configuration

Configure the Datadog endpoint to forward Cisco Duo logs to Datadog.

1. Navigate to `Cisco Duo`.
2. Add your Cisco Duo credentials.

| Cisco Duo Parameters | Description  |
| -------------------- | ------------ |
| Host                 | The API Hostname from Cisco Duo. It is the `XXXXXXXX` part of `https://api-XXXXXXXX.duosecurity.com`.  |
| Integration Key      | The Integration Key from Cisco Duo.    |
| Secret Key           | The Secret Key from Cisco Duo.         |

## Data Collected

### Logs

The Cisco Duo integration collects and forwards Cisco Duo Authentication, Activity, Administrator, Telephony and Offline Enrollment logs to Datadog.

### Metrics

The Cisco Duo integration does not include any metrics.

### Events

The Cisco Duo integration does not include any events.

## Support

For further assistance, contact [Datadog Support][4].

[1]: https://duo.com/
[2]: https://signup.duo.com/
[3]: https://admin.duosecurity.com/
[4]: https://docs.datadoghq.com/help/