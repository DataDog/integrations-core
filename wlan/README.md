# Agent Check: wlan

## Overview

This check monitors Wireless LAN (WLAN) networks based on the [IEEE 802.11][1] standards, commonly referred to as Wi-Fi.

It collects key Wi-Fi metrics, including Access Point (AP) information such as [SSID][2] and [BSSID][3] (as tags), signal quality telemetry like [RSSI][4] and [Noise][5], transmission rate, and transitions count ([Roaming][6] and [Swapping][7] between APs, for example). These metrics help proactively identify overall wireless network issues, such as overloaded access points, as well as retrospective troubleshooting of poor network performance on individual hosts.

**Minimum Agent version:** 7.64.2

## Setup

### Prerequisite

#### Windows

Starting from Windows 11 24H2 (Fall 2024), according to [Changes to API behavior for Wi-Fi access and location][16], WLAN Check (which uses Windows Wlan APIs), requires user or administrator consent. If the host's `Settings > Privacy & security > Location` has not been enabled, this WLAN check will fail to report WLAN/Wi-Fi telemetry.

The following settings need to be enabled:
- **Settings > Privacy & security > Location > Location services**
- **Settings > Privacy & security > Location > Let desktop apps access your location**

You can check if the Location API is not disabled by running `netsh wlan show interface` command, which would fail to report any Wi-Fi interface connection even if you are connected.

An administrator can also enable these settings using the following:
- [Registry][17]
- [Group Policy][18]
- [InTune][19]


#### macOS

Just like on Windows, Wi-Fi telemetry collection on macOS requires user consent through location services. However, unlike Windows, macOS does not provide a well-defined mechanism for administrators to enable location access for specific processes like the Datadog Agent at scale.

To work around this, customers can adapt the `add_datadog_agent_to_plist.sh` script provided in **Appendix** to grant location access to the Agent process. This script requires **root** access and can be deployed across an enterprise Mac fleet using an MDM solution like Jamf.

### Installation

The WLAN check is included in the [Datadog Agent][8], but is not configured. Please see the next section to configure the check.

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

WLAN does not include any events.

## Terminology

### Roaming

`Roaming` refers to a device's ability to seamlessly switch from one Wi-Fi access point to another as it moves around, without losing its connection. This happens when the device finds a stronger or more reliable signal from a different access point, ensuring continuous internet access. A `Roaming` event is detected when the *BSSID* of the connected router or AP has been changed but its *SSID* is still the same.  When the *SSID* of the router or AP is not broadcasted, roaming detection is not possible. When a `Roaming` event is detected, the `system.wlan.roaming_events` metric is then incremented. Switching to a router with a different *SSID* is not considered to be `Roaming`.

### Channel Swap

`Channel Swap` refers to the process of changing the Wi-Fi channel a router or access point is using to broadcast its signal. This is done to improve signal strength, reduce interference, or optimize performance, especially in areas with many competing Wi-Fi networks. The `Channel Swap` event is detected when the *BSSID* of the connected router or access point is the same but its channel has been changed. When the *BSSID* of the connected router or access point has been changed (which makes it a `Roaming` event if the router or access point has the same *SSID*) it is not considered a `Channel Swap` event even if the channel has been changed.

## Troubleshooting

Need help? Contact [Datadog support][15].

## Appendix

**add_datadog_agent_to_plist.sh**

```shell script
#!/usr/bin/env bash
# Script to add/update the authorized key in `locationd/clients.plist` for the Datadog agent (requires root access)
# Usage: bash add_datadaog_agent_to_plist.sh [AGENT_BIN_PATH]
# AGENT_BIN_PATH: optional - the agent binary path - default: /opt/datadog-agent/bin/agent/agent

# Configuration
PLIST_PATH="/var/db/locationd/clients.plist"
DEFAULT_PATTERN="/opt/datadog-agent/bin/agent/agent"
BACKUP_PATH="${PLIST_PATH}.bak"

# Function to restore backup if something goes wrong
restore_backup() {
  echo "[ERROR] Restoring backup..."
  sudo cp "$BACKUP_PATH" "$PLIST_PATH"
  sudo plutil -convert binary1 "$PLIST_PATH"
  echo "[INFO] Backup restored. Exiting."
  exit 1
}

# Set up error handling
trap restore_backup ERR

# Check if an argument was provided
if [ -n "$1" ]; then
  PATTERN="$1"
  echo "[INFO] Using provided pattern via CLI argument: $PATTERN"
else
  # Prompt for pattern to search for
  read -p "Enter the pattern to search for [${DEFAULT_PATTERN}]: " PATTERN
  PATTERN=${PATTERN:-$DEFAULT_PATTERN}
fi

# Backup the original file
echo "[INFO] Backing up $PLIST_PATH to $BACKUP_PATH"
sudo cp "$PLIST_PATH" "$BACKUP_PATH"

# Convert plist to XML for easier parsing
sudo plutil -convert xml1 "$PLIST_PATH"

echo "[INFO] Searching for entry containing: $PATTERN"

# Find the first key whose block contains the pattern, xargs removes leading and trailing whitespaces
KEY_LINE=$(grep "$PATTERN" "$PLIST_PATH" | grep "<key>" | head -n1 | xargs)
if [ -z "$KEY_LINE" ]; then
  echo "[ERROR] No entry found containing pattern: $PATTERN"
  restore_backup
fi

# Extract the key from the line
KEY=${KEY_LINE#<key>}
KEY=${KEY%</key>}

if [ -z "$KEY" ]; then
  echo "[ERROR] Could not determine the key for the matching entry."
  restore_backup
fi

echo "[INFO] Processing key: $KEY"

# Get the line number containing <key>$KEY</key>
key_line=$(grep -n "<key>$KEY</key>" "$PLIST_PATH" | cut -d: -f1 | head -n1)
if [ -z "$key_line" ]; then
  echo "[ERROR] Key not found."
  restore_backup
fi

# Get the line number of the <dict> after the key
dict_start=$(tail -n +$((key_line + 1)) "$PLIST_PATH" | grep -n "<dict>" | head -n1 | cut -d: -f1)
dict_start=$((key_line + dict_start))

# Get the line number of the matching </dict>
dict_end=$(tail -n +$((dict_start + 1)) "$PLIST_PATH" | grep -n "</dict>" | head -n1 | cut -d: -f1)
dict_end=$((dict_start + dict_end))

echo "[INFO] Found block from line $dict_start to $dict_end"

# Check if <key>Authorized</key> exists in the block
auth_line=$(sed -n "${dict_start},${dict_end}p" "$PLIST_PATH" | grep -n "<key>Authorized</key>" | cut -d: -f1)

if [ -z "$auth_line" ]; then
  # <key>Authorized</key> not found, add it before </dict>
  echo "[INFO] Adding <key>Authorized</key><true/> to the block"
  sed -i "" "${dict_end}i\\
		<key>Authorized</key>\\
		<true/>\\
" "$PLIST_PATH"
else
  # <key>Authorized</key> found, check the next line for its value
  auth_line=$((dict_start + auth_line - 1))
  value_line=$((auth_line + 1))
  
  # Check if the next line contains <false/>
  if grep -q "<false/>" <(sed -n "${value_line}p" "$PLIST_PATH"); then
    echo "[INFO] Changing <false/> to <true/>"
    sed -i "" "${value_line}s/<false\/>/<true\/>/" "$PLIST_PATH"
  else
    echo "[INFO] <key>Authorized</key> already exists with correct value"
  fi
fi

# Convert plist back to binary for system use
sudo plutil -convert binary1 "$PLIST_PATH"
echo "[INFO] Changes applied successfully."
echo "[INFO] To apply changes, either reboot or run: sudo killall locationd"
trap - ERR
```

[1]: https://en.wikipedia.org/wiki/IEEE_802.11
[2]: https://en.wikipedia.org/wiki/Service_set_(802.11_network)#SSID
[3]: https://en.wikipedia.org/wiki/Service_set_(802.11_network)
[4]: https://en.wikipedia.org/wiki/Received_signal_strength_indicator
[5]: https://documentation.meraki.com/MR/Wi-Fi_Basics_and_Best_Practices/Signal-to-Noise_Ratio_(SNR)_and_Wireless_Signal_Strength
[6]: https://www.netally.com/tech-tips/what-is-wifi-roaming/
[7]: https://superuser.com/questions/122441/how-can-i-get-the-same-ssid-for-multiple-access-points
[8]: https://app.datadoghq.com/account/settings/agent/latest
[9]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/
[10]: https://github.com/DataDog/datadog-agent/blob/main/cmd/agent/dist/conf.d/wlan.d/conf.yaml.example
[11]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[12]: https://docs.datadoghq.com/getting_started/tagging/
[13]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[14]: https://github.com/DataDog/integrations-core/blob/master/wlan/metadata.csv
[15]: https://docs.datadoghq.com/help/
[16]: https://learn.microsoft.com/en-us/windows/win32/nativewifi/wi-fi-access-location-changes
[17]: https://learn.microsoft.com/en-us/troubleshoot/windows-client/shell-experience/cannot-set-timezone-automatically?WT.mc_id=WDIT-MVP-5000497#use-registry-editor
[18]: https://learn.microsoft.com/en-us/troubleshoot/windows-client/shell-experience/cannot-set-timezone-automatically?WT.mc_id=WDIT-MVP-5000497#use-registry-editor
[19]: https://learn.microsoft.com/en-us/troubleshoot/windows-client/shell-experience/cannot-set-timezone-automatically?WT.mc_id=WDIT-MVP-5000497#use-registry-editor
