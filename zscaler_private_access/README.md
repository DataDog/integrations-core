# Zscaler Private Access

## Overview

The [Zscaler Private Access][5] (ZPA) service enables organizations to provide access to internal applications and services while ensuring the security of their networks. ZPA is an easier-to-deploy and a more cost-effective and secure alternative to VPNs. Unlike VPNs, which require users to connect to your network to access your enterprise applications, ZPA provides policy-based secure access so users are only given access to the internal apps they need.

The integration parses and ingests the following types of logs:
- User Activity
- User Status
- App Connector Metrics
- App Connector Status
- Private Service Edge Metrics
- Private Service Edge Status
- Browser Access
- Audit Logs
- AppProtection
- Private Cloud Controller Status
- Private Cloud Controller Metrics
- Microsegmentation Flow.

Datadog uses its built-in log pipelines to parse and enrich these logs, facilitating easy search and detailed insights. Visualize detailed insights into these logs with out-of-the-box dashboards. Additionally, the integration includes ready-to-use Cloud SIEM detection rules and monitors for enhanced monitoring and security.

## Setup

### Installation

The Zscaler Private Access check is included in the [Datadog Agent][1] package. No additional installation is needed on your server. 

### Configuration

#### Log collection

1. Collecting logs is disabled by default in the Datadog Agent. Enable it in `datadog.yaml`:

   ```yaml
   logs_enabled: true
   ```

2. Add this configuration block to your `zscaler_private_access.d/conf.yaml` file to start collecting your logs.

   See the sample [zscaler_private_access.d/conf.yaml][6] for available configuration options.

   ```yaml
   logs:
     - type: tcp
       port: <PORT>
       source: zscaler-private-access
   ```

   **Note**:

   - `PORT`: Port should be similar to the port provided in **Configure log receiver from Zscaler Private Access** section.
   - It is recommended not to change the source value, as these parameters are integral to the pipeline's operation.

3. [Restart the Agent][2].

#### Configure log receiver from Zscaler Private Access

1. Sign in to the Zscaler Private Access (ZPA) Admin Portal.
2. Go to **Configuration & Control > Private Infrastructure > LOG STREAMING SERVICE > Log Receivers**.
3. Click **Add**.
4. In the **Log Receiver** tab, configure the following:
    - **Name**: Provide a name for the log receiver.
    - **Domain or IP Address**: Enter the public IP or hostname of the Datadog Agent that will receive the logs.
    - **TCP Port**: Specify an open port on the Datadog Agent for receiving ZPA logs.
    - **TLS Encryption**: Keep it disabled.
    - **App Connector Groups**: Choose the App Connector groups that can forward logs to the receiver.
5. Click **Next**.
6. In the **Log Stream** tab:
    - **Log Type**: Select from the below supported log types.
      > Note: Create a separate log receiver for each log type.
      - User Activity
      - User Status
      - App Connector Metrics
      - App Connector Status
      - Private Service Edge Metrics
      - Private Service Edge Status
      - Browser Access
      - Audit Logs
      - AppProtection
      - Private Cloud Controller Status
      - Private Cloud Controller Metrics
      - Microsegmentation Flow
    - **Log Stream Content**: For each selected log type, paste the provided custom log format from below **Log Formats** section.
    - **Log Template**: When you paste the custom log format, the log template will be set to **Custom** by default.
7. Click **Next**.
8. Review your configuration on the **Review** tab and click **Save**.

#### Log Formats
For Zscaler Private Access integration, specific custom log formats must be configured for each supported log type. The required formats for each log type are outlined below.

   1. **User Activity Log**
   ```
   {"LogTimestamp": %j{LogTimestamp:time},"Customer": %j{Customer},"SessionID": %j{SessionID},"ConnectionID": %j{ConnectionID},"InternalReason": %j{InternalReason},"ConnectionStatus": %j{ConnectionStatus},"IPProtocol": %d{IPProtocol},"DoubleEncryption": %d{DoubleEncryption},"Username": %j{Username},"ServicePort": %d{ServicePort},"ClientPublicIP": %j{ClientPublicIP},"ClientPrivateIP": %j{ClientPrivateIP},"ClientLatitude": %f{ClientLatitude},"ClientLongitude": %f{ClientLongitude},"ClientCountryCode": %j{ClientCountryCode},"ClientZEN": %j{ClientZEN},"Policy": %j{Policy},"Connector": %j{Connector},"ConnectorZEN": %j{ConnectorZEN},"ConnectorIP": %j{ConnectorIP},"ConnectorPort": %d{ConnectorPort},"Host": %j{Host},"Application": %j{Application},"AppGroup": %j{AppGroup},"Server": %j{Server},"ServerIP": %j{ServerIP},"ServerPort": %d{ServerPort},"PolicyProcessingTime": %d{PolicyProcessingTime},"ServerSetupTime": %d{ServerSetupTime},"TimestampConnectionStart": %j{TimestampConnectionStart:iso8601},"TimestampConnectionEnd": %j{TimestampConnectionEnd:iso8601},"TimestampCATx": %j{TimestampCATx:iso8601},"TimestampCARx": %j{TimestampCARx:iso8601},"TimestampAppLearnStart": %j{TimestampAppLearnStart:iso8601},"TimestampZENFirstRxClient": %j{TimestampZENFirstRxClient:iso8601},"TimestampZENFirstTxClient": %j{TimestampZENFirstTxClient:iso8601},"TimestampZENLastRxClient": %j{TimestampZENLastRxClient:iso8601},"TimestampZENLastTxClient": %j{TimestampZENLastTxClient:iso8601},"TimestampConnectorZENSetupComplete": %j{TimestampConnectorZENSetupComplete:iso8601},"TimestampZENFirstRxConnector": %j{TimestampZENFirstRxConnector:iso8601},"TimestampZENFirstTxConnector": %j{TimestampZENFirstTxConnector:iso8601},"TimestampZENLastRxConnector": %j{TimestampZENLastRxConnector:iso8601},"TimestampZENLastTxConnector": %j{TimestampZENLastTxConnector:iso8601},"ZENTotalBytesRxClient": %d{ZENTotalBytesRxClient},"ZENBytesRxClient": %d{ZENBytesRxClient},"ZENTotalBytesTxClient": %d{ZENTotalBytesTxClient},"ZENBytesTxClient": %d{ZENBytesTxClient},"ZENTotalBytesRxConnector": %d{ZENTotalBytesRxConnector},"ZENBytesRxConnector": %d{ZENBytesRxConnector},"ZENTotalBytesTxConnector": %d{ZENTotalBytesTxConnector},"ZENBytesTxConnector": %d{ZENBytesTxConnector},"Idp": %j{Idp},"ClientToClient": %j{c2c},"ClientCity": %j{ClientCity},"MicroTenantID": %j{MicroTenantID},"AppMicroTenantID": %j{AppMicroTenantID},"Platform": %j{Platform},"Hostname": %j{Hostname},"AppLearnTime": %d{AppLearnTime},"CAProcessingTime": %d{CAProcessingTime},"ConnectionSetupTime": %d{ConnectionSetupTime},"ConnectorZENSetupTime": %d{ConnectorZENSetupTime},"PRAApprovalID": %j{PRAApprovalID},"PRACapabilityPolicyID": %j{PRACapabilityPolicyID},"PRAConnectionID": %j{PRAConnectionID},"PRAConsoleType": %j{PRAConsoleType},"PRACredentialLoginType": %j{PRACredentialLoginType},"PRACredentialPolicyID": %j{PRACredentialPolicyID},"PRACredentialUserName": %j{PRACredentialUserName},"PRAErrorStatus": %j{PRAErrorStatus},"PRAFileTransferList": %j{PRAFileTransferList},"PRARecordingStatus": %j{PRARecordingStatus},"PRASessionType": %j{PRASessionType},"PRASharedMode": %j{PRASharedMode},"PRASharedUserList": %j{PRASharedUserList},"EventType": "user-activity"}\n
   ```

   2. **User Status Log**
   ```
   {"LogTimestamp": %j{LogTimestamp:time},"Customer": %j{Customer},"Username": %j{Username},"SessionID": %j{SessionID},"SessionStatus": %j{SessionStatus},"Version": %j{Version},"ZEN": %j{ZEN},"CertificateCN": %j{CertificateCN},"PrivateIP": %j{PrivateIP},"PublicIP": %j{PublicIP},"Latitude": %f{Latitude},"Longitude": %f{Longitude},"CountryCode": %j{CountryCode},"TimestampAuthentication": %j{TimestampAuthentication:iso8601},"TimestampUnAuthentication": %j{TimestampUnAuthentication:iso8601},"TotalBytesRx": %d{TotalBytesRx},"TotalBytesTx": %d{TotalBytesTx},"Idp": %j{Idp},"Hostname": %j{Hostname},"Platform": %j{Platform},"ClientType": %j{ClientType},"TrustedNetworks": [%j(,){TrustedNetworks}],"TrustedNetworksNames": [%j(,){TrustedNetworksNames}],"PosturesHit": [%j(,){PosturesHit}],"PosturesMiss": [%j(,){PosturesMiss}],"ZENLatitude": %f{ZENLatitude},"ZENLongitude": %f{ZENLongitude},"ZENCountryCode": %j{ZENCountryCode},"FQDNRegistered": %j{fqdn_registered},"FQDNRegisteredError": %j{fqdn_register_error},"City": %j{City},"MicroTenantID": %j{MicroTenantID},"SAMLAttributes": %j{SAMLAttributes},"EventType": "user-status"}\n
   ```

   3. **App Connector Metrics Log**
   ```
   {"LogTimestamp":%j{LogTimestamp:time},"Connector":%j{Connector},"CPUUtilization":%j{CPUUtilization},"SystemMemoryUtilization":%j{SystemMemoryUtilization},"ProcessMemoryUtilization":%j{ProcessMemoryUtilization},"AppCount":%j{AppCount},"ServiceCount":%j{ServiceCount},"TargetCount":%j{TargetCount},"AliveTargetCount":%j{AliveTargetCount},"ActiveConnectionsToPublicSE":%j{ActiveConnectionsToPublicSE},"DisconnectedConnectionsToPublicSE":%j{DisconnectedConnectionsToPublicSE},"ActiveConnectionsToPrivateSE":%j{ActiveConnectionsToPrivateSE},"DisconnectedConnectionsToPrivateSE":%j{DisconnectedConnectionsToPrivateSE},"TransmittedBytesToPublicSE":%j{TransmittedBytesToPublicSE},"ReceivedBytesFromPublicSE":%j{ReceivedBytesFromPublicSE},"TransmittedBytesToPrivateSE":%j{TransmittedBytesToPrivateSE},"ReceivedBytesFromPrivateSE":%j{ReceivedBytesFromPrivateSE},"AppConnectionsCreated":%j{AppConnectionsCreated},"AppConnectionsCleared":%j{AppConnectionsCleared},"AppConnectionsActive":%j{AppConnectionsActive},"UsedTCPPortsIPv4":%j{UsedTCPPortsIPv4},"UsedUDPPortsIPv4":%j{UsedUDPPortsIPv4},"UsedTCPPortsIPv6":%j{UsedTCPPortsIPv6},"UsedUDPPortsIPv6":%j{UsedUDPPortsIPv6},"AvailablePorts":%j{AvailablePorts},"SystemMaximumFileDescriptors":%j{SystemMaximumFileDescriptors},"SystemUsedFileDescriptors":%j{SystemUsedFileDescriptors},"ProcessMaximumFileDescriptors":%j{ProcessMaximumFileDescriptors},"ProcessUsedFileDescriptors":%j{ProcessUsedFileDescriptors},"AvailableDiskBytes":%j{AvailableDiskBytes},"MicroTenantID": %j{MicroTenantID},"EventType": "app-connector-metrics"}\n
   ```

   4. **App Connector Status Log**
   ```
   {"LogTimestamp": %j{LogTimestamp:time},"Customer": %j{Customer},"SessionID": %j{SessionID},"SessionType": %j{SessionType},"SessionStatus": %j{SessionStatus},"Version": %j{Version},"Platform": %j{Platform},"ZEN": %j{ZEN},"Connector": %j{Connector},"ConnectorGroup": %j{ConnectorGroup},"PrivateIP": %j{PrivateIP},"PublicIP": %j{PublicIP},"Latitude": %f{Latitude},"Longitude": %f{Longitude},"CountryCode": %j{CountryCode},"TimestampAuthentication": %j{TimestampAuthentication:iso8601},"TimestampUnAuthentication": %j{TimestampUnAuthentication:iso8601},"CPUUtilization": %d{CPUUtilization},"MemUtilization": %d{MemUtilization},"ServiceCount": %d{ServiceCount},"InterfaceDefRoute": %j{InterfaceDefRoute},"DefRouteGW": %j{DefRouteGW},"PrimaryDNSResolver": %j{PrimaryDNSResolver},"HostStartTime": %j{HostStartTime},"ConnectorStartTime": %j{ConnectorStartTime},"NumOfInterfaces": %d{NumOfInterfaces},"BytesRxInterface": %d{BytesRxInterface},"PacketsRxInterface": %d{PacketsRxInterface},"ErrorsRxInterface": %d{ErrorsRxInterface},"DiscardsRxInterface": %d{DiscardsRxInterface},"BytesTxInterface": %d{BytesTxInterface},"PacketsTxInterface": %d{PacketsTxInterface},"ErrorsTxInterface": %d{ErrorsTxInterface},"DiscardsTxInterface": %d{DiscardsTxInterface},"TotalBytesRx": %d{TotalBytesRx},"TotalBytesTx": %d{TotalBytesTx},"MicroTenantID": %j{MicroTenantID},"EventType": "app-connector-status"}\n
   ```

   5. **Private Service Edge Metrics Log**
   ```
   {"LogTimestamp":%j{LogTimestamp:time},"PrivateSE":%j{PrivateSE},"CPUUtilization":%j{CPUUtilization},"SystemMemoryUtilization":%j{SystemMemoryUtilization},"ProcessMemoryUtilization":%j{ProcessMemoryUtilization},"UsedTCPPortsIPv4":%j{UsedTCPPortsIPv4},"UsedUDPPortsIPv4":%j{UsedUDPPortsIPv4},"UsedTCPPortsIPv6":%j{UsedTCPPortsIPv6},"UsedUDPPortsIPv6":%j{UsedUDPPortsIPv6},"AvailablePorts":%j{AvailablePorts},"SystemMaximumFileDescriptors":%j{SystemMaximumFileDescriptors},"SystemUsedFileDescriptors":%j{SystemUsedFileDescriptors},"ProcessMaximumFileDescriptors":%j{ProcessMaximumFileDescriptors},"ProcessUsedFileDescriptors":%j{ProcessUsedFileDescriptors},"AvailableDiskBytes":%j{AvailableDiskBytes},"MicroTenantID": %j{MicroTenantID},"EventType": "private-service-edge-metrics"}\n
   ```

   6. **Private Service Edge Status Log**
   ```
   {"LogTimestamp": %j{LogTimestamp:time},"Customer": %j{Customer},"SessionID": %j{SessionID},"SessionType": %j{SessionType},"SessionStatus": %j{SessionStatus},"Version": %j{Version},"PackageVersion": %j{PackageVersion},"Platform": %j{Platform},"ZEN": %j{ZEN},"ServiceEdge": %j{ServiceEdge},"ServiceEdgeGroup": %j{ServiceEdgeGroup},"PrivateIP": %j{PrivateIP},"PublicIP": %j{PublicIP},"Latitude": %f{Latitude},"Longitude": %f{Longitude},"CountryCode": %j{CountryCode},"TimestampAuthentication": %j{TimestampAuthentication:iso8601},"TimestampUnAuthentication": %j{TimestampUnAuthentication:iso8601},"CPUUtilization": %d{CPUUtilization},"MemUtilization": %d{MemUtilization},"InterfaceDefRoute": %j{InterfaceDefRoute},"DefRouteGW": %j{DefRouteGW},"PrimaryDNSResolver": %j{PrimaryDNSResolver},"HostUpTime": %j{HostUpTime},"ServiceEdgeStartTime": %j{ServiceEdgeStartTime},"NumOfInterfaces": %d{NumOfInterfaces},"BytesRxInterface": %d{BytesRxInterface},"PacketsRxInterface": %d{PacketsRxInterface},"ErrorsRxInterface": %d{ErrorsRxInterface},"DiscardsRxInterface": %d{DiscardsRxInterface},"BytesTxInterface": %d{BytesTxInterface},"PacketsTxInterface": %d{PacketsTxInterface},"ErrorsTxInterface": %d{ErrorsTxInterface},"DiscardsTxInterface": %d{DiscardsTxInterface},"TotalBytesRx": %d{TotalBytesRx},"TotalBytesTx": %d{TotalBytesTx},"MicroTenantID": %j{MicroTenantID},"EventType": "private-service-edge-status"}\n
   ```

   7. **Browser Access Log**
   ```
   {"LogTimestamp":%j{LogTimestamp:time},"ConnectionID":%j{ConnectionID},"Exporter":%j{Exporter},"TimestampRequestReceiveStart":%j{TimestampRequestReceiveStart:iso8601},"TimestampRequestReceiveHeaderFinish":%j{TimestampRequestReceiveHeaderFinish:iso8601},"TimestampRequestReceiveFinish":%j{TimestampRequestReceiveFinish:iso8601},"TimestampRequestTransmitStart":%j{TimestampRequestTransmitStart:iso8601},"TimestampRequestTransmitFinish":%j{TimestampRequestTransmitFinish:iso8601},"TimestampResponseReceiveStart":%j{TimestampResponseReceiveStart:iso8601},"TimestampResponseReceiveFinish":%j{TimestampResponseReceiveFinish:iso8601},"TimestampResponseTransmitStart":%j{TimestampResponseTransmitStart:iso8601},"TimestampResponseTransmitFinish":%j{TimestampResponseTransmitFinish:iso8601},"TotalTimeRequestReceive":%d{TotalTimeRequestReceive},"TotalTimeRequestTransmit":%d{TotalTimeRequestTransmit},"TotalTimeResponseReceive":%d{TotalTimeResponseReceive},"TotalTimeResponseTransmit":%d{TotalTimeResponseTransmit},"TotalTimeConnectionSetup":%d{TotalTimeConnectionSetup},"TotalTimeServerResponse":%d{TotalTimeServerResponse},"Method":%j{Method},"Protocol":%j{Protocol},"Host":%j{Host},"URL":%j{URL},"UserAgent":%j{UserAgent},"XFF":%j{XFF},"NameID":%j{NameID},"StatusCode":%d{StatusCode},"RequestSize":%d{RequestSize},"ResponseSize":%d{ResponseSize},"ApplicationPort":%d{ApplicationPort},"ClientPublicIp":%j{ClientPublicIp},"ClientPublicPort":%d{ClientPublicPort},"ClientPrivateIp":%j{ClientPrivateIp},"Customer":%j{Customer},"ConnectionStatus":%j{ConnectionStatus},"ConnectionReason":%j{ConnectionReason},"Origin":%j{Origin},"CorsToken":%j{CorsToken},"EventType": "browser-access"}\n
   ```

   8. **Audit Log**
   ```
   {"ModifiedTime":%j{modifiedTime:iso8601},"CreationTime":%j{creationTime:iso8601},"ModifiedBy":%d{modifiedBy},"RequestID":%j{requestId},"SessionID":%j{sessionId},"AuditOldValue":%j{auditOldValue},"AuditNewValue":%j{auditNewValue},"AuditOperationType":%j{auditOperationType},"ObjectType":%j{objectType},"ObjectName":%j{objectName},"ObjectID":%d{objectId},"CustomerID":%d{customerId},"User":%j{modifiedByUser},"ClientAuditUpdate":%d{clientAuditUpdate},"EventType": "audit-logs"}\n
   ```

   9. **AppProtection Log**
   ```
   {"LogTimestamp": %j{LogTimestamp:time},"Customer": %j{Customer},"ConnectionID": %j{ConnectionID},"UserID": %j{UserID},"AssistantID": %j{AssistantID},"ExchangeSequenceIndex": %d{ExchangeSequenceIndex},"TimestampRequestReceiveStart": %d{TimestampRequestReceiveStart},"TimestampRequestReceiveHeaderFinish": %d{TimestampRequestReceiveHeaderFinish},"TimestampRequestReceiveFinish": %d{TimestampRequestReceiveFinish},"TimestampRequestTransmitStart": %d{TimestampRequestTransmitStart},"TimestampRequestTransmitFinish": %d{TimestampRequestTransmitFinish},"TimestampResponseReceiveFinish": %d{TimestampResponseReceiveFinish},"TimestampResponseTransmitStart": %d{TimestampResponseTransmitStart},"TimestampResponseTransmitFinish": %d{TimestampResponseTransmitFinish},"TotalTimeRequestReceive": %d{TotalTimeRequestReceive},"TotalTimeRequestTransmit": %d{TotalTimeRequestTransmit},"TotalTimeResponseReceive": %d{TotalTimeResponseReceive},"TotalTimeResponseTransmit": %d{TotalTimeResponseTransmit},"Domain": %j{Domain},"Method": %j{Method},"Protocol": %j{Protocol},"ProtocolVersion": %j{ProtocolVersion},"ContentType": %j{ContentType},"ContentEncoding": %j{ContentEncoding},"TransferEncoding": %j{TransferEncoding},"Host": %j{Host},"Destination": %j{Destination},"OriginDomain": %j{OriginDomain},"URL": %j{URL},"UserAgent": %j{UserAgent},"HTTPError": %j{HTTPError},"ClientPublicIp": %j{ClientPublicIp},"ClientPort": %d{ClientPort},"UpgradeHeaderPresent": %d{UpgradeHeaderPresent},"StatusCode": %d{StatusCode},"RequestHdrSize": %d{RequestHdrSize},"ResponseHdrSize": %d{ResponseHdrSize},"RequestBodySize": %d{RequestBodySize},"ResponseBodySize": %d{ResponseBodySize},"Application": %d{Application},"ApplicationGroup": %d{ApplicationGroup},"InspectionPolicy": %d{InspectionPolicy},"InspectionProfile": %d{InspectionProfile},"ParanoiaLevel": %d{ParanoiaLevel},"InspectionControlsHitCount": %d{InspectionControlsHitCount},"InspectionRuleProcessingTime": %d{InspectionRuleProcessingTime},"InspectionReqHeadersProcessingTime": %d{InspectionReqHeadersProcessingTime},"InspectionReqBodyProcessingTime": %d{InspectionReqBodyProcessingTime},"InspectionRespHeadersProcessingTime": %d{InspectionRespHeadersProcessingTime},"InspectionRespBodyProcessingTime": %d{InspectionRespBodyProcessingTime},"CertificateId": %d{CertificateId},"DoubleEncryption": %d{DoubleEncryption},"SSLInspection": %d{SSLInspection},"TotalBytesProcessed": %d{TotalBytesProcessed},"InspectionControls": [%j(,){InspectionControlArray}],"InspectionControlTypes": [%j(,){ControlTypeArray}],"InspectionControlCategories": [%j(,){InspectionControlCategories}],"Actions": [%j(,){Actions}],"Severities": [%j(,){SeveritiesArray}],"Descriptions": [%j(,){DescriptiveExplanationsArray}],"EventType": "app-protection"}\n
   ```

   10. **Private Cloud Controller Status**
   ```
   {"LogTimestamp": %j{LogTimestamp:time},"Customer": %j{Customer},"SessionID": %j{SessionID},"SessionType": %j{SessionType},"SessionStatus": %j{SessionStatus},"Version": %j{Version},"Platform": %j{Platform},"ZEN": %j{ZEN},"PrivateCloudController":%j{PrivateCloudController},"PrivateCloudControllerGroup":%j{PrivateCloudControllerGroup},"PrivateIP":%j{PrivateIP},"PublicIP":%j{PublicIP},"PackageVersion": %j{PackageVersion},"Latitude": %f{Latitude},"Longitude": %f{Longitude},"CountryCode": %j{CountryCode},"TimestampAuthentication": %j{TimestampAuthentication:iso8601},"TimestampUnAuthentication": %j{TimestampUnAuthentication:iso8601},"CPUUtilization": %d{CPUUtilization},"MemUtilization": %d{MemUtilization},"InterfaceDefRoute": %j{InterfaceDefRoute},"DefRouteGW": %j{DefRouteGW},"PrimaryDNSResolver": %j{PrimaryDNSResolver},"HostUpTime": %j{HostUpTime},"PrivateCloudControllerStartTime": %j{PrivateCloudControllerStartTime},"NumOfInterfaces": %d{NumOfInterfaces},"BytesRxInterface": %d{BytesRxInterface},"PacketsRxInterface": %d{PacketsRxInterface},"ErrorsRxInterface": %d{ErrorsRxInterface},"DiscardsRxInterface": %d{DiscardsRxInterface},"BytesTxInterface": %d{BytesTxInterface},"PacketsTxInterface": %d{PacketsTxInterface},"ErrorsTxInterface": %d{ErrorsTxInterface},"DiscardsTxInterface": %d{DiscardsTxInterface},"TotalBytesRx": %d{TotalBytesRx},"TotalBytesTx": %d{TotalBytesTx},"MicroTenantID": %j{MicroTenantID},"EventType": "private-cloud-controller-status"}\n
   ```

   11. **Private Cloud Controller Metrics**
   ```
   {"LogTimestamp":%j{LogTimestamp:time},"PrivateCloudController":%j{PrivateCloudController},"CPUUtilization":%d{CPUUtilization},"SystemMemoryUtilization":%j{SystemMemoryUtilization},"ProcessMemoryUtilization":%j{ProcessMemoryUtilization},"UsedTCPPortsIPv4":%j{UsedTCPPortsIPv4},"UsedUDPPortsIPv4":%j{UsedUDPPortsIPv4},"UsedTCPPortsIPv6":%j{UsedTCPPortsIPv6},"UsedUDPPortsIPv6":%j{UsedUDPPortsIPv6},"AvailablePorts":%j{AvailablePorts},"SystemMaximumFileDescriptors":%j{SystemMaximumFileDescriptors},"SystemUsedFileDescriptors":%j{SystemUsedFileDescriptors},"ProcessMaximumFileDescriptors":%j{ProcessMaximumFileDescriptors},"ProcessUsedFileDescriptors":%j{ProcessUsedFileDescriptors},"AvailableDiskBytes":%j{AvailableDiskBytes},"EventType": "private-cloud-controller-metrics"}\n
   ```

   12. **Microsegmentation Flow**
   ```
   {"LogTimestamp": %j{LogTimestamp:time},"Customer": %j{Customer},"AgentID": %j{AgentID},"AgentName": %j{AgentName},"ResourceID": %j{ResourceID},"ResourceName": %j{ResourceName},"AppZoneID": %j{AppZoneID},"AppName": %j{AppName},"AppZoneName": %j{AppZoneName},"ConnectionStartTime": %j{ConnectionStartTime},"SourceIP": %j{SourceIP},"DestinationIP": %j{DestinationIP},"SourcePorts": %j{SourcePorts},"DestinationPort": %j{DestinationPort},"Protocol": %j{Protocol},"AppExecutablePath": %j{AppExecutablePath},"Direction": %j{Direction},"PolicyID": %j{PolicyID},"PolicyName": %j{PolicyName},"EnforcementReason": %j{EnforcementReason},"EnforcementAction": %j{EnforcementAction},"EnforcementDisposition": %j{EnforcementDisposition},"EventType": "microsegmentation"}\n
   ```


#### Validation

[Run the Agent's status subcommand][3] and look for `zscaler_private_access` under the Checks section.

## Data Collected

### Logs

The Zscaler Private Access integration collects and forwards User Activity, User Status, App Connector Metrics, App Connector Status, Private Service Edge Metrics, Private Service Edge Status, Browser Access, Audit Logs, AppProtection, Private Cloud Controller Status, Private Cloud Controller Metrics, Microsegmentation Flow logs to Datadog.

### Metrics

The Zscaler Private Access integration does not include any metrics.

### Events

The Zscaler Private Access integration does not include any events.

## Troubleshooting

### Permission denied while port binding

If you see a **Permission denied** error while port binding in the Agent logs:

   1. Binding to a port number under 1024 requires elevated permissions. Grant access to the port using the `setcap` command:

      ```shell
      sudo setcap CAP_NET_BIND_SERVICE=+ep /opt/datadog-agent/bin/agent/agent
      ```

   2. Verify the setup is correct by running the `getcap` command:

      ```shell
      sudo getcap /opt/datadog-agent/bin/agent/agent
      ```

      With the expected output:

      ```shell
      /opt/datadog-agent/bin/agent/agent = cap_net_bind_service+ep
      ```

      **Note**: Re-run this `setcap` command every time you upgrade the Agent.

   3. [Restart the Agent][2].

### Data is not being collected

Ensure firewall settings allow traffic through the configured port.

### Port already in use

On systems running Syslog, the Agent may fail to bind to port 514 and display the following error: 
   
    `Can't start UDP forwarder on port 514: listen udp :514: bind: address already in use`

This error occurs because Syslog uses port 514 by default. 

To resolve:
  - Disable Syslog, OR
  - Configure the Agent to listen on a different, available port.

## Support

For further assistance, contact [Datadog support][4].

[1]: /account/settings/agent/latest
[2]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[4]: https://docs.datadoghq.com/help/
[5]: https://www.zscaler.com/products-and-solutions/zscaler-private-access
[6]: https://github.com/DataDog/integrations-core/blob/master/zscaler_private_access/datadog_checks/zscaler_private_access/data/conf.yaml.example
