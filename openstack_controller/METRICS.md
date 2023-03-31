# Nova

## Limits
In Nova OpenStack, limits are a way to enforce quotas on the usage of resources by individual users or projects. Limits are enforced to ensure that resources are fairly distributed among all users and to prevent any single user or project from consuming too many resources.

| Datadog Metric      | Openstack Metric | Description                                           |
|-----------------------|----------------|-------------------------------------------------------|
| openstack.nova.limits.max_server_group_members |maxServerGroupMembers| The number of allowed members for each server group.|  
|openstack.nova.limits.max_server_groups|maxServerGroups| The number of allowed server groups for each tenant. | 
|openstack.nova.limits.max_server_meta|maxServerMeta| The number of allowed metadata items for each server. |
|openstack.nova.limits.max_total_cores|maxTotalCores| The number of allowed server cores for each tenant.   |
|openstack.nova.limits.max_total_instances|maxTotalInstances| The number of allowed servers for each tenant.   |     
|openstack.nova.limits.max_total_keypairs|maxTotalKeypairs|The number of allowed key pairs for each user.|
|openstack.nova.limits.max_total_ram_size|maxTotalRAMSize|The amount of allowed server RAM, in MiB, for each tenant.|
|openstack.nova.limits.total_cores_used|totalCoresUsed|The number of used server cores in each tenant.|
|openstack.nova.limits.total_instances_used|totalInstancesUsed|The number of servers in each tenant.|
|openstack.nova.limits.total_ram_used|totalRAMUsed|The amount of used server RAM in each tenant.|
|openstack.nova.limits.total_server_groups_used|totalServerGroupsUsed|The number of used server groups in each tenant.|
|openstack.nova.limits.max_security_group_rules|maxSecurityGroupRules|The number of allowed rules for each security group. **Available until version 2.35**
|openstack.nova.limits.max_security_groups|maxSecurityGroups|The number of allowed security groups for each tenant. **Available until version 2.35**
|openstack.nova.limits.max_total_floating_ips|maxTotalFloatingIps|The number of allowed floating IP addresses for each tenant. **Available until version 2.35**
|openstack.nova.limits.total_floating_ips_used|totalFloatingIpsUsed|The number of used floating IP addresses in each tenant. **Available until version 2.35**
|openstack.nova.limits.total_security_groups_used|totalSecurityGroupsUsed|The number of used security groups in each tenant. **Available until version 2.35**
|openstack.nova.limits.max_image_meta|maxImageMeta|The number of allowed metadata items for each image. **Available until version 2.38**
|openstack.nova.limits.max_personality|maxPersonality|The number of allowed injected files for each tenant. **Available until version 2.56**
|openstack.nova.limits.max_personality_size|maxPersonalitySize|The number of allowed bytes of content for each injected file. **Available until version 2.56**


