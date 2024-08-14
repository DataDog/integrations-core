## Goal
Detect incidents where spyware or grayware has been identified on endpoints. This indicates potential privacy breaches, unwanted monitoring, or less severe but still significant threats that can compromise endpoint security and user privacy.

## Strategy
Monitor alerts from Trend Micro Vision One Endpoint Security for detections of spyware or grayware. Correlate these alerts to evaluate the scope and impact, pinpointing the affected endpoints and understanding the potential threat vectors. This helps in assessing the seriousness of the threat and planning appropriate remediation actions.

## Triage and Response
1.  Identify the affected endpoint using its name - `{{source_host_name}}` and IP address - `{{endpoint_ip}}`.
2.  Review the virus name - `{{virus_name}}` to understand the specific spyware or grayware detected.
3.  Isolate the affected endpoint to prevent any potential spread or further compromise.
4.  Remove or quarantine the detected spyware or grayware to mitigate risks.
5.  Perform a thorough scan on the endpoint to ensure no additional threats are present.