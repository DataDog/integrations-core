# Bitdefender Integration For Datadog

## Overview

[Bitdefender][1] provides cybersecurity solutions with leading security efficacy, performance and ease of use to small and medium businesses, mid-market enterprises and consumers. Bitdefender EDR effectively stops ransomware and breaches with automated cross-endpoint correlation and seamlessly integrated prevention, protection, detection and response.

The Bitdefender integration ingests the logs using the Webhook. Following are the event types for which integration provides OOTB dashboards and detection rules:

- **Antiphishing:** This event is generated each time the endpoint agent detects a known phishing attempt when accessing a web page.
- **Antimalware:** This event is generated each time Bitdefender detects malware on an endpoint in your network.
- **Advanced Threat Control (ATC):** This event is created whenever a potentially dangerous applications is detected and blocked on an endpoint.
- **Data Protection:** This event is generated each time the data traffic is blocked on an endpoint, according to data protection rules.
- **Exchange Malware Detection:** This event is created when Bitdefender detects malware on an Exchange server in your network.
- **Firewall:** This event is generated when the endpoint agent blocks a port scan or an application from accessing the network, according to the applied policy.
- **Hyper Detect event:** This event is generated when a malware is detected by the Hyper Detect module.
- **Sandbox Analyzer Detection:** This event is generated each time Sandbox Analyzer detects a new threat among the submitted files.
- **Antiexploit Event:** This event is generated when Advanced Anti-Exploit triggers a detection.
- **Network Attack Defense Event:** This event is generated when the Network Attack Defense module triggers a detection.
- **User Control/Content Control:** This event is generated when a user activity such as web browsing of software application is blocked on the endpoint according to the applied policy.
- **Storage Antimalware Event:** This event is generated each time SVA detects a new threat among the protected storage (NAS).
- **Ransomware activity detection:** This event occurs when the endpoint agent blocks ransomware attack.
- **New Incident:** This event is generated every time a new Root Cause Analysis (RCA) is displayed under the Incidents section of Control Center. The event contains a list of relevant items extracted from the RCA JSON.

## Setup

### Configuration

#### Bitdefender Configuration

##### Steps to Create API Key on Bitdefender Business Security Enterprise Portal:
1. Log in to Bitdefender Business Security Enterprise Portal.
2. On the right-hand side, select **User Role** and click on **My Account**.
3. Navigate to the **API keys** section.
4. Click on the **Add**. Pop-up form will open up for API Key Configuration.
5. Provide the following information:
    - API Key Description: <\Provide any relevant name>
    - Enabled APIs: Select Event Push Service.
6. Click on **Generate** and copy the generated Api key. 
7. Perform Base64 encoding on the generated Api key as described below:
    - Take your API key and append a colon (\:) to it, like this: ```<api_key>:```
    - Encode the resulting string using a Base64 encoder.
    - For example:

      - If your API key is abc123, the string to encode is abc123:.
      - After Base64 encoding, the result will be something like: YWJjMTIzOg==.

8. Note down the encoded API key for webhook configuration.
9. Navigate to the **Control Center API** section and note down the Access URL. This URL will be used in the curl command as **\<control_center_apis_access_url>**.

Reference: [API Key and Authentication Reference Document][3]

##### Steps to Configure Webhook via Datadog:
- Navigate to **Integrations** tab on your Datadog cloud account and search for Bitdefender integration.
- Over Configure tab of Bitdefender integration, select an existing API key or create a new one by selecting any of the buttons.
- After selecting API key, Click on **Add API key** button and copy the URL by clicking on **Click Here to Copy URL**.
- Execute curl command as mentioned below after updating/replacing following fields: 
    - **\<control_center_apis_access_url>**: \<collected from the above section>
    - **\<bitdefender-encoded-api-key>**: \<encoded api key>
    - **\<dd-api-key>**: \<datadog api key>
    - **\<webhook_url>**:  \<URL copied from the above step>
```bash
curl -X POST -k "<control_center_apis_access_url>/v1.0/jsonrpc/push" --header "Authorization: Basic <bitdefender-encoded-api-key>" --header "Content-Type: application/json" --data "{\"params\": {\"status\": 1,\"serviceType\": \"jsonRPC\",\"serviceSettings\": {\"url\": \"<webhook_url>\",\"requireValidSslCertificate\": false,\"authorization\": \"<dd-api-key>\"},\"subscribeToEventTypes\": {\"av\": true,\"aph\": true,\"fw\": true,\"avc\": true,\"uc\": true,\"dp\": true,\"hd\": true,\"exchange-malware\": true,\"network-sandboxing\": true,\"new-incident\": true,\"antiexploit\": true,\"network-monitor\": true,\"ransomware-mitigation\": true,\"storage-antimalware\": true}},\"jsonrpc\": \"2.0\",\"method\": \"setPushEventSettings\",\"id\": \"bitdefender_push\"}"
```

- After replacing/updating above fields curl command looks like below:
```bash
curl -X POST -k "https://cloudap.gravityzone.bitdefender.com/api/v1.0/jsonrpc/push" --header "Authorization: Basic <bitdefender-encoded-api-key>" --header "Content-Type: application/json" --data "{\"params\": {\"status\": 1,\"serviceType\": \"jsonRPC\",\"serviceSettings\": {\"url\": \"https://http-intake.logs.datadoghq.com/api/v2/logs?dd-api-key=<dd-api-key>&ddsource=bitdefender\",\"requireValidSslCertificate\": false,\"authorization\": \"<dd-api-key>\"},\"subscribeToEventTypes\": {\"av\": true,\"aph\": true,\"fw\": true,\"avc\": true,\"uc\": true,\"dp\": true,\"hd\": true,\"exchange-malware\": true,\"network-sandboxing\": true\"new-incident\": true,\"antiexploit\": true,\"network-monitor\": true,\"ransomware-mitigation\": true,\"storage-antimalware\": true,}},\"jsonrpc\": \"2.0\",\"method\": \"setPushEventSettings\",\"id\": \"bitdefender_push\"}"

```
**Note:** For windows machine add `^` before `&ddsource` in **webhook_url** parameter.

	
- Once you execute the curl command, json response with the result key having true value would return that means your connection is established successfully.
- Ensure the data is being received in datadog by filtering logs using below query in Log explorer.
  - source: bitdefender

## Data Collected

### Logs

The Bitdefender integration collects and forwards Bitdefender logs to Datadog.

### Metrics

The Bitdefender integration does not include any metrics.

### Events

The Bitdefender integration does not include any events.

## Support

For further assistance, contact [Datadog Support][2].

[1]: https://www.bitdefender.com/en-in/business/products/endpoint-detection-response
[2]: https://docs.datadoghq.com/help/
[3]: https://www.bitdefender.com/business/support/en/77209-125277-public-api.html#UUID-2a74c3b5-6159-831d-4f8a-ca42797ce3b0_section-idm4640169987334432655171029621