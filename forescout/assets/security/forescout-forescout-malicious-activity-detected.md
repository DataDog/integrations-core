## Goal  
Detect when a malicious event is identified by another appliance and reported to Forescout, which may indicate a threat within the network.

## Strategy  
Monitor Syslog messages for alerts forwarded from other security appliances that have detected potentially malicious activity. These events help identify threats early and enable a quick response.

## Triage and Response  
1. Identify the source endpoint IP `{{@network.client.ip}}` involved in the reported activity.  
2. Treat the detection as a potential threat and initiate an investigation to determine if further evidence of malicious behavior exists.  
3. Review related Syslog and network logs to gather additional context and assess potential impact.  
4. If confirmed malicious, isolate the endpoint, take appropriate remediation steps, and review security controls to prevent recurrence.  