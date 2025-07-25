# Bitdefender integration for Datadog

## Overview

[Bitdefender][1] provides cybersecurity solutions with leading security efficacy, performance, and ease of use to small and medium businesses, mid-market enterprises, and consumers. Bitdefender EDR effectively stops ransomware and breaches with automated cross-endpoint correlation and seamlessly integrated prevention, protection, detection, and response.

The Bitdefender integration uses a webhook to ingest Bitdefender EDR logs. The integration provides OOTB dashboards and detection rules for the following event types:

| Event                         | Trigger                                                                                                                                                           |
|-------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Antiphishing                  | Endpoint agent detects a known phishing attempt when accessing a web page                                                                                         |
| Antimalware                   | Bitdefender detects malware on an endpoint in your network                                                                                                        |
| Advanced Threat Control (ATC) | Potentially dangerous application is detected and blocked on an endpoint                                                                                          |
| Data Protection               | Data traffic is blocked on an endpoint, according to data protection rules                                                                                        |
| Exchange Malware Detection    | Bitdefender detects malware on an Exchange server in your network                                                                                                 |
| Firewall                      | Endpoint agent blocks a port scan or an application from accessing the network, according to the applied policy                                                   |
| Hyper Detect event            | Hyper Detect module detects malware                                                                                                                               |
| Sandbox Analyzer Detection    | Sandbox Analyzer detects a new threat among the submitted files                                                                                                   |
| Antiexploit Event             | Advanced Anti-Exploit triggers a detection                                                                                                                        |
| Network Attack Defense Event  | Network Attack Defense module triggers a detection                                                                                                                |
| User Control/Content Control  | User activity, such as web browsing of software application, is blocked on the endpoint according to the applied policy                                           |
| Ransomware activity detection | Endpoint agent blocks ransomware attack                                                                                                                           |
| New Incident                  | New Root Cause Analysis (RCA) is displayed under the Incidents section of Control Center. The event contains a list of relevant items extracted from the RCA JSON |

## Setup

### Retrieve the Datadog Webhook URL

1. In Datadog, navigate to the **Integrations** tab, and search for the Bitdefender integration.
2. Click the **Bitdefender** integration. The integration window opens. On the **Configure** tab, select an existing API key, or create a new one.
3. After selecting an API key, click **Add API key**, then **Click Here to Copy URL**.

### Configure a webhook in Bitdefender

1. Log in to Bitdefender Business Security Enterprise Portal using an administrator account. Your account must have the following rights:
   - Manage Networks
   - Manage Users
   - Manage Company
   - View and analyze data
2. Click the **User menu**, then click **My Account**.
3. Navigate to the **Control Center API** section and copy the Access URL.
4. Navigate to the **API keys** section.
5. Click **Add**. The API Key Configuration window opens.
6. Provide the following information:
    - **API Key Description**: A relevant name for your API key
    - **Enabled APIs**: Select Event Push Service.
7. Click **Generate** and copy the generated API key. 
8. Perform Base64 encoding on the generated API key. You need to use the encoded API key for webhook configuration.
    1. Take your API key and append a colon (\:) to it, like this: `<api_key>:`
    2. Encode the resulting string using a Base64 encoder.
    
    For example, if your API key is abc123, the string to encode is `abc123:` After Base64 encoding, the result will be something like `YWJjMTIzOg==`.

9. Make a curl request. Use the template below, putting values into the following fields: 
    - **\<control_center_apis_access_url>**: The URL you copied in step 3
    - **\<bitdefender-encoded-api-key>**: Your encoded API key from step 8
    - **\<dd-api-key>**: Your Datadog API key
    - **\<webhook_url>**:  The URL you copied in previous section `Retrieve the Datadog Webhook URL`
        - **Note**: If you're using Windows, add `^` before `&ddsource` and `&service` in the **webhook_url** parameter.
    - **\<event-type>**: The event type for which logs need to be pushed to Datadog, e.g. `av` for Antimalware
        - Supported event types: `aph` (Antiphishing), `av` (Antimalware), `avc` (Advanced Threat Control), `dp` (Data Protection), `exchange-malware` (Exchange Malware Detection), `fw` (Firewall), `hd` (Hyper Detect event), `network-sandboxing` (Sandbox Analyzer Detection), `antiexploit`, `network-monitor` (Network Attack Defense Event), `uc` (User Control/Content Control), `ransomware-mitigation` (Ransomware activity detection), `new-incident`
    
    ```bash
    curl -X POST -k "<control_center_apis_access_url>/v1.0/jsonrpc/push" --header "Authorization: Basic <bitdefender-encoded-api-key>" --header "Content-Type: application/json" --data "{\"params\": {\"status\": 1,\"serviceType\": \"jsonRPC\",\"serviceSettings\": {\"url\": \"<webhook_url>\",\"requireValidSslCertificate\": false,\"authorization\": \"<dd-api-key>\"},\"subscribeToEventTypes\": {\"<event-type>\": true}},\"jsonrpc\": \"2.0\",\"method\": \"setPushEventSettings\",\"id\": 1}"
    ```

10. Repeat steps 5-9 for each supported event type you want to push to Datadog.

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