# MUX

## Overview

[Mux][1] is an all-in-one video streaming platform. It offers APIs and tools for video hosting, live streaming, etc. enabling users to easily create, manage, and optimize video content. Mux provides scalable video infrastructure to build seamless video experiences. 

Integrate Mux with Datadog to gain insights into mux video performance data.

## Setup

### Get config parameters from Mux

#### Find your Access Token ID and Secret Key from Mux
1. Login to [MUX account][2].
2. In the sidebar, click on **Settings**.
3. Click on **Access Tokens**.
4. Select **Generate new token**.
5. Choose the environment.
6. Under the **permission** section, select **Mux Data(read-only)**.
7. Enter the access token name.
8. Click on **Generate Token**.
9. Save the Access Token ID and Secret Key from the **Here's your new Access Token** tab.

### Add your Mux credentials
- Access token ID 
- Secret key

## Data Collected

### Logs

The Mux integration does not include any logs.

### Metrics

The Mux integration collects and forwards mux metrics data to Datadog. See [metadata.csv][4] for a list of metrics provided by this integration.

### Service Checks

The Mux integration does not include any service checks.

### Events

The Mux integration does not include any events.

## Troubleshooting

Need help? Contact [Datadog support][3].

[1]: https://www.mux.com/
[2]: https://dashboard.mux.com/
[3]: https://docs.datadoghq.com/help/
[4]: https://github.com/DataDog/integrations-core/blob/master/mux/metadata.csv
