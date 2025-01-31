# Mimecast

## Overview

[Mimecast][1] is a cloud-based solution designed to protect organizations from a wide range of email-based threats. The product offers a comprehensive set of security features that help to safeguard against advanced threats, such as phishing, malware, spam, and targeted attacks, while also providing data leak prevention and email continuity services.

This integration ingests the following logs:

- Audit : Audit logs allow you to search, review, and export logs regarding account access and configuration changes made by administrators.
- DLP : Data Loss Prevention (DLP) is a set of practices designed to secure confidential business data as well as detect and head off data loss resulting from breaches and malicious attacks.
- Rejection : Rejected messages contain a virus signature, or destined to a recipient that doesn't exist. In these instances no email data is accepted by Mimecast, and Rejected messages cannot be retrieved.
- TTP Attachment : Targeted Threat Protection(TTP) Attachment Protection protects customers from spear phishing attacks that use email attachments.
- TTP Impersonation : Targeted Threat Protection(TTP) Impersonation Protect helps prevent impersonation attacks by scanning emails in real time for signs of an attack.
- TTP URL : Targeted Threat Protection(TTP) URL Protection is an email security service that rewrites all inbound email links and scans the destination website in real-time when clicked by the user.

The Mimecast integration seamlessly collects all the above listed logs, channeling them into Datadog for analysis. Leveraging the built-in logs pipeline, these logs are parsed and enriched, enabling effortless search and analysis. The integration provides insight into audit, DLP, malicious attachments in email, email sent by user as an impersonated identity, phishing email links, and many more through the out-of-the-box dashboards.

## Setup

### Generate API credentials in Mimecast

1. Log into your **Mimecast account**.
2. Navigate to the **Administration Console**, select **Services**, and then choose the **API and Platform Integrations** section.
3. Proceed to Your **API 2.0 Applications**.
4. Search for your application in the list provided.
5. If the application is absent, it means it hasn't been set up yet, and you'll need to configure it with the following steps:
   - In **API and Platform Integrations** page, click on **Available Integrations** tab.
   - Click the **Generate keys** button of Mimecast API 2.0 tile.
   - Check the **I accept** checkbox, click on **Next**.
   - In **Application Details** step, fill out the following details according to the instructions:
     - Application Name: Enter a meaningful name for the application
     - Category: Select **SIEM Integration**
     - Products: Click **Select all** option
     - Application Role: Select **Basic Administrator**
     - Description: Enter the description of your choice
   - In **Notifications**, provide the contact details of your technical administrator and click on **Next**
   - Click on **Add and Generate Keys**. A pop up window appears, showing the client ID and client secret.
6. If the application is present, click on its name.
7. Click the **Manage API 2.0 credentials** button and click **Generate**. This generates a new Client ID and Client Secret.

### Connect your Mimecast account to Datadog

1. Add your Mimecast credentials.

    | Parameters | Description                                                           |
    | ------------------- | ------------------------------------------------------------ |
    | Client ID           | The client ID of your registered application on Mimecast.     |
    | Client Secret       | The client secret of your registered application on Mimecast. |

2. Click the Save button to save your settings.

## Data Collected

### Logs

The Mimecast integration collects and forwards Mimecast Audit, DLP, Rejection, TTP Attachment and TTP Impersonation, TTP URL logs to Datadog.

### Metrics

The Mimecast integration does not include any metrics.

### Service Checks

The Mimecast integration does not include any service checks.

### Events

The Mimecast integration does not include any events.

## Support

Need help? Contact [Datadog Support][2].

[1]: https://www.mimecast.com/
[2]: https://docs.datadoghq.com/help/
