## Overview

[Mimecast][1] is a cloud-based solution designed to protect organizations from a wide range of email-based threats. The product offers a comprehensive set of security features that help to safeguard against advanced threats, such as phishing, malware, spam, and targeted attacks, while also providing data leak prevention and email continuity services.

This integration ingests the following logs:

- Audit
- DLP
- Rejection
- TTP Attachment
- TTP Impersonation
- TTP URL

The Mimecast integration seamlessly collects all the above listed logs, channeling them into Datadog for analysis. Leveraging the built-in logs pipeline, these logs are parsed and enriched, enabling effortless search and analysis. The integration provides insight into audit, dlp, malicious attachment attached in email, email send by user as an impersonated identity, phishing email links, and many more through the out-of-the-box dashboards.

## Setup

### Configuration

#### Get Credentials of Mimecast

To find your application's details in Mimecast Email Security:

1. Sign into Mimecast Email Security with your credentials.
2. Navigate to the **Administration Console**, select **Services**, and then choose the **API and Platform Integrations** section.
3. Proceed to Your **API 2.0 Applications**.
4. Search for your application in the list provided.
5. If the application is absent, it means it hasn't been set up yet, and you'll need to configure it so follow below steps:
   - In **API and Platform Integrations** page, click on **Available Integrations** tab.
   - After that, click on **Generate keys** button of Mimecast API 2.0 tile.
   - Checked **I accept** checkbox, click on **Next**
   - In **Application Details** step, fill details as per below instructions:
     - Application Name: Enter the application name of your choice
     - Category: Select **SIEM Integration**
     - Products: Click on **Select all** option
     - Application Role: Select **SIEM Admin Role**
     - Description: Enter the description of your choice
   - In **Notifications**, provide a contact details of your technical person and click on **Next**
   - After clicking on **Add and Generate Keys** there will be pop up window showing Client ID and Client Secret. Please copy those keys to some safe place since they won't be displayed again.
6. If the application is present, then click on its name.
7. After that, click on **Manage API 2.0 credentials** button and then click on **Generate**. So it will generate new Client ID and Client Secret. Please copy those keys to some safe place since they won't be displayed again.

#### Mimecast DataDog Integration Configuration

Configure the Datadog endpoint to forward Mimecast logs to Datadog.

1. Navigate to `Mimecast`.
2. Add your Mimecast credentials.

| Mimecast Parameters | Description                                                  |
| ------------------- | ------------------------------------------------------------ |
| Client ID           | The Client ID of your registered application on mimecast     |
| Client Secret       | The Client Secret of your registered application on mimecast |

## Data Collected

### Logs

The Mimecast integration collects and forwards Mimecast Audit, DLP, Rejection, TTP Attachment and TTP Impersonation, TTP URL logs to Datadog.

### Metrics

The Mimecast integration does not include any metrics.

### Events

The Mimecast integration does not include any events.

## Support

For further assistance, contact [Datadog Support][2].

[1]: https://www.mimecast.com/
[2]: https://docs.datadoghq.com/help/
