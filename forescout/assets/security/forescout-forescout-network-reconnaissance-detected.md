## Goal  
Detect when an endpoint performs multiple network probes within a short period, indicating possible network reconnaissance activity.

## Strategy  
Monitor for repeated network scanning activity from endpoints that may signal reconnaissance efforts or malicious intent.

## Triage and Response  
1. Identify the endpoint IP `{{@network.client.ip}}` involved in the scanning activity.  
2. Verify whether this behavior is part of authorized network testing or appears suspicious.  
3. Review Syslog and network logs to understand the frequency and pattern of the connection attempts.  
4. If the activity is unauthorized, block or isolate the endpoint, investigate potential threats, and update network monitoring and security policies accordingly.  