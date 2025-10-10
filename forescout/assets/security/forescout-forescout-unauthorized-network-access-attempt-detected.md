## Goal  
Detect when an endpoint tries to access your network using a system mark, which could indicate an unauthorized access attempt or a misconfigured device.

## Strategy  
Monitor Syslog messages for connection attempts using a system mark. These events can help identify suspicious or unauthorized network access early.

## Triage and Response  
1. Identify the endpoint IP `{{@network.client.ip}}`, destination IP `{{@network.destination.ip}}`, and destination port `{{@network.destination.port}}` involved in the access attempt.  
2. Verify if the access attempt was authorized or if it appears suspicious or unauthorized.  
3. Review related Syslog and network logs for additional details or repeated attempts from the same source.  
4. If the attempt is unauthorized, block the endpoint IP, investigate for potential security issues, and update network policies or device configurations as needed.  