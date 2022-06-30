## Overview

Collect Edgecast metrics to monitor your web traffic by origin.

## Setup

### Create Edgecast Client 

1. Login to your [Edgecast VDMS account][1] and navigate to the **Clients** tab.
2. Click **Create New Client** to bring up the New Client modal.
3. Input a unique identifying client name and click **Toggle all ec.analytics** to allow this client to collect metrics.
4. Navigate to **Settings** and modify **JWT Expiration in Seconds** to 600.
5. Click **Save** to save this client and the modified settings value.

### Configuration

1. Navigate to the configuration tab inside the Datadog [Edgecast integration tile][2].
2. Enter a unique identifying name for this client in Datadog. 
3. Paste the Client ID and Client Secret from the Edgecast Client created above.
   * Find the Client ID after `client_id=` in the **Getting an access token** request under the **Quick Start** tab of your configured Edgecast Client.
   * Find the Client Secret under the **Client Secrets** tab of your configured Edgecast Client.
4. Optionally, add custom tags to associate them with all metrics collected for this integration.
   * Metrics are automatically tagged with the Edgecast name associated with the origin. 

## Data Collected

### Metrics

See [metadata.csv][3] for a list of metrics provided by this integration.

### Events

The Edgecast integration does not include any events.

### Service Checks

The Edgecast integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][4].

[1]: https://id.vdms.io
[2]: https://app.datadoghq.com/account/settings#integrations/edgecast-cdn
[3]: https://github.com/DataDog/dogweb/blob/prod/integration/edgecast_cdn/edgecast_cdn_metadata.csv
[4]: https://docs.datadoghq.com/help
