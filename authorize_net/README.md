# Authorize.Net

## Overview
[Authorize.Net][1] is a payment gateway that allows businesses to accept secure payments through various channels, including online, mobile, and in-person transactions. It supports a range of payment methods such as credit cards, e-checks, and digital wallets, and offers a versatile solution for merchants. The platform emphasizes security with features like encryption, tokenization, and PCI DSS compliance, while also providing advanced fraud detection tools.

The Authorize.Net integration collects settled transaction logs and unsettled transaction metrics, and forwards them to Datadog for comprehensive analysis.

## Setup

### Generate Login ID and Transaction Key in Authorize.Net

#### Login ID

1. Visit the appropriate URL:
   - For a production environment, visit [login.authorize.net][2].
   - For a sandbox environment, visit [sandbox.authorize.net][5].
2. Sign in to your Authorize.Net account with a user which has access to the **Account Administrator** role.
3. Go to **Account > Security Settings > General Security Settings**.
4. Click **API Credentials & Keys**. 
5. Use the API Login ID as the `Login ID` value when you [connect your Authorize.Net account to Datadog](#connect-your-authorizenet-account-to-datadog).

#### Transaction Key

1. On the same page, click **New Transaction Key** and then **Submit**.
2. A popup is displayed to verify your identity; click **Request PIN**.
3. Enter the PIN you received through email, and click **Verify PIN**.
4. Use the Transaction Key value when you [connect your Authorize.Net account to Datadog](#connect-your-authorizenet-account-to-datadog).
5. Click **Continue**.

### Connect your Authorize.Net Account to Datadog

1. Add your Login ID, Transaction Key, and Environment Type.

   |Parameters| Description                                                                                    |
   |--------------------|------------------------------------------------------------------------------------------------|
   |Login ID| API Login ID for your Authorize.Net account.                                                        |
   |Transaction Key| Transaction Key for your Authorize.Net account.                                                 |
   |Environment Type| Dropdown to select the environment type for your Authorize.Net account (Production or Sandbox). |

2. Click the **Save** button to save your settings.

## Data Collected

### Logs

The Authorize.Net integration collects and forwards settled transaction logs to Datadog.

### Metrics

The Authorize.Net integration collects and forwards unsettled transaction metrics to Datadog.

{{< get-metrics-from-git "authorize_net" >}}

### Events

The Authorize.Net integration does not include any events.

## Support

For further assistance, contact [Datadog Support][4].

[1]: https://www.authorize.net/
[2]: https://login.authorize.net/
[3]: https://github.com/DataDog/integrations-core/blob/master/Authorize.Net/metadata.csv
[4]: https://docs.datadoghq.com/help/
[5]: https://sandbox.authorize.net/