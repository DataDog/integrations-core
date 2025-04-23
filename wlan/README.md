# Agent Check: wlan

## Overview

This check monitors Wireless LAN (WLAN) networks based on the [IEEE 802.11][1] standards, commonly referred to as Wi-Fi.

It collects key Wi-Fi metrics, including Access Point (AP) information such as [SSID][2] and [BSSID][3] (as tags), signal quality telemetry like [RSSI][4] and [Noise][5], transmission rate, and transitions count (e.g., [Roaming][6] and [Swapping][7] between APs). These metrics help proactively identify overall wireless network issues, such as overloaded access points, as well as retrospective troubleshooting of poor network performance on individual hosts.

## Setup

### Installation

The wlan check is included in the [Datadog Agent][8], but is not configured. Please see the next section to configure the check.

### Configuration

The configuration is located in the `wlan.d/conf.yaml` file in the `conf.d/` folder at the root of your [Agent's configuration directory][9]. See the [sample wlan.d/conf.yaml][10] for all available configuration options. When you are done editing the configuration file, [restart the Agent][11] to load the new configuration.

#### Tags

The check automatically tags emitted metrics with SSID, BSSID, MAC Address, Wi-Fi type (A, B, G, N, AC), Wi-Fi Authentication (Open, WEP, WPA, WPA2, WPA3). As noted in [Getting Started with Tags][12] uppercase characers in tag values are replaced by lowercase characters and special characters are replaced with underscores.

### Validation

[Run the Agent's status subcommand][13] and look for `wlan` under the **Checks** section.

## Data Collected

### Metrics

See [metadata.csv][14] for a list of metrics provided by this integration.

### Events

wlan does not include any events.

## Terminology

### Roaming

`Roaming` refers to a device's ability to seamlessly switch from one Wi-Fi access point to another as it moves around, without losing its connection. This happens when the device finds a stronger or more reliable signal from a different access point, ensuring continuous internet access. `Roaming` event is detected when the *BSSID* of the connected Router or AP has been changed but its *SSID* is still the same.  When the *SSID* of the Router or AP is not broadcasted Roaming detection is not possible. When a `Roaming` event is detected then `wlan.roaming_events` metric is incremented. Switch to router with a different *SSID* is not considered `Roaming`.

### Channel Swap

`Channel Swap` refers to the process of changing the Wi-Fi channel a router or Access Point is using to broadcast its signal. This is done to improve signal strength, reduce interference, or optimize performance, especially in areas with many competing Wi-Fi networks. `Channel Swap` event is detected when the *BSSID* of the connected Router or AP is the same but its channel had been changed. When the *BSSID* of the connected Router or AP had been changed (which makes it `Roaming` event if the Router or AP has the same *SSID*) it will not be considered as `Channel Swap` event even if the channel has been changed.

## Troubleshooting

Need help? Contact [Datadog support][15].

[1]: https://en.wikipedia.org/wiki/IEEE_802.11
[2]: https://en.wikipedia.org/wiki/Service_set_(802.11_network)#SSID
[3]: https://en.wikipedia.org/wiki/Service_set_(802.11_network)
[4]: https://en.wikipedia.org/wiki/Received_signal_strength_indicator
[5]: https://documentation.meraki.com/MR/Wi-Fi_Basics_and_Best_Practices/Signal-to-Noise_Ratio_(SNR)_and_Wireless_Signal_Strength
[6]: https://www.netally.com/tech-tips/what-is-wifi-roaming/
[7]: https://superuser.com/questions/122441/how-can-i-get-the-same-ssid-for-multiple-access-points
[8]: https://app.datadoghq.com/account/settings/agent/latest
[9]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/
[10]: https://github.com/DataDog/datadog-agent/blob/main/poc/cmd/agent/dist/conf.d/wlan.d/conf.yaml.example
[11]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[12]: https://docs.datadoghq.com/getting_started/tagging/
[13]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[14]: https://github.com/DataDog/integrations-core/blob/master/wlan/metadata.csv
[15]: https://docs.datadoghq.com/help/
