# Agent Check: Palo Alto Networks Firewall

## Overview

This check monitors [Palo Alto Networks firewalls][1] through the Datadog Agent.

Palo Alto Networks next-generation firewalls run PAN-OS and enforce security policy, threat prevention, and VPN connectivity at the network edge and in the data center. This integration polls the PAN-OS XML API of each firewall, either from a static list or from the firewalls that a Panorama server manages, collects health and performance metrics, and reports the firewalls and their interfaces to Network Device Monitoring (NDM). It also parses the threat, traffic, authentication, and other logs that PAN-OS forwards through syslog.

### What this integration monitors

The integration collects metrics across multiple layers of the firewall, including:

- **Firewall inventory**: Discovers firewalls from a static list or from Panorama, and reports them to NDM with their serial number, model, software version, and high availability (HA) state.
- **System resources**: Reports management-plane CPU, memory, swap, and disk usage, and data-plane CPU utilization, to detect overloaded firewalls. Hardware firewalls also report power and temperature sensors.
- **Network interfaces**: Provides traffic, errors, drops, and attack counters per interface. Reports each interface to NDM with its description and admin status.
- **IPsec tunnels**: Reports tunnel state and traffic, and the number of active, inactive, and initializing tunnels.
- **Routing**: Reports BGP peer state and prefix counts, and OSPF neighbor state, to detect a routing peer going down.
- **Licenses**: Reports expiration status and days left for each subscription.
- **Security rules and threats**: Provides hit counts per security rule, and threat counts by severity, action, and subtype alongside the threat logs.
- **Global counters and reports** (optional): Collects PAN-OS global counters, dropped packets by aspect, and top-N reports for applications, sources, destinations, zones, and rules.

**Minimum Agent version:** 7.86.0

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][3] for guidance on applying these instructions.

### Installation

The Palo Alto Networks Firewall check is included in the [Datadog Agent][2] package.
No additional installation is needed on your server.

### Configuration

1. Create an account for the Agent on each firewall. In PAN-OS, go to **Device > Admin Roles** and add a role profile with an **XML API** tab that allows **Operational Requests**, **Report**, and **Log**. Then go to **Device > Administrators**, add an account that uses this role, and commit the changes.

   **Note**: For Panorama discovery, also create an account on Panorama with a role that allows **Operational Requests** in the XML API tab. The Agent uses it only to list the managed firewalls, and polls each firewall with the matching `firewall_credentials` entry.

2. Edit the `pan_firewall.d/conf.yaml` file, in the `conf.d/` folder at the root of your Agent's configuration directory to start collecting your Palo Alto Networks firewall performance data. See the [sample pan_firewall.d/conf.yaml][4] for all available configuration options.

   **Note**: The Agent connects to the management interface of each firewall over HTTPS. HTTPS must be enabled in the management profile of that interface, and if you restrict management access, the Agent host must be in the **Permitted IP Addresses** list. With Panorama discovery, the Agent polls each firewall at the IP address that Panorama reports for it.

   PAN-OS management interfaces ship with a self-signed certificate. Either install a certificate signed by a certificate authority (CA) that the Agent trusts, or set `tls_verify` to `false`.

   If you use Panorama discovery, configure `firewall_ips` with an explicit include list that matches your known firewall IP ranges, so that the check only connects to expected firewalls.

3. [Restart the Agent][5].

### Validation

[Run the Agent's status subcommand][6] and look for `pan_firewall` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][7] for a list of metrics provided by this integration.

The integration submits a gauge only when its PAN-OS call runs, so each gauge series has one point per interval of its group. Size monitor evaluation windows to match:

- Every 2 minutes: BGP peer metrics and data-plane CPU utilization.
- Every 3 minutes: management-plane CPU, memory, and swap, IPsec tunnel and OSPF neighbor metrics.
- Every 5 minutes: power and temperature sensors.
- Every 30 minutes: disk usage, interface speed, and top-N report metrics.
- Every 24 hours: license days left and expiration.

### Logs

The Palo Alto Networks Firewall integration collects the logs that PAN-OS forwards through syslog, as described in the [PAN-OS documentation][8].

1. Enable log collection in your `datadog.yaml` file:

    ```yaml
    logs_enabled: true
    ```

   **Note**: Install the Agent on a host that the firewall can reach on the syslog port and that can connect to the internet.
2. Edit the logs configuration block in your `pan_firewall.d/conf.yaml` file. For example:

    ```yaml
    logs:
      - type: tcp
        port: 10518
        source: pan.firewall
        service: <SERVICE>
    ```
3. In PAN-OS, go to **Device > Server Profiles > Syslog** and add a server profile with the IP address of the Agent host, transport **TCP**, port **10518**, and format **BSD**.
4. In the **Custom Log Format** tab of the server profile, configure the format for each log type you want to collect. The formats below map the fields listed in the [PAN-OS syslog field descriptions][9].

    | Name     	                   | Format                                                |
    | -------------------------------| ---------------------------------------------------------- |
    | Traffic Log | <details> <summary><i> View Payload </i> </summary> <p><code>timestamp=$time_generated, serial=$serial, type=$type, subtype=$subtype, time_generated=$time_generated, network.client.ip=$src, network.destination.ip=$dst, natsrc=$natsrc, natdst=$natdst, rule=$rule, usr.id=$srcuser, dstuser=$dstuser,	app=$app,	vsys=$vsys,	source_zone=$from,	destination_zone=$to,	inbound_if=$inbound_if,	outbound_if=$outbound_if,	logset=$logset,	sessionid=$sessionid,	repeatcnt=$repeatcnt,	network.client.port=$sport,	network.destination.port=$dport, natsport=$natsport	natdport=$natdport,	flags=$flags,	proto=$proto,	 evt.name=$action,	bytes=$bytes,	network.bytes_read=$bytes_sent,	network.bytes_written=$bytes_received, start=$start, elapsed=$elapsed, category=$category,	seqno=$seqno,	actionflags=$actionflags,	network.client.geoip.country.name=$srcloc,	dstloc=$dstloc,	pkts_sent=$pkts_sent, pkts_received=$pkts_received, session_end_reason=$session_end_reason,	device_name=$device_name,	action_source=$action_source,	src_uuid=$src_uuid,	dst_uuid=$dst_uuid,	tunnelid=$tunnelid, imsi= $imsi, monitortag=$monitortag, imei=$imei,	parent_session_id=$parent_session_id,	parent_start_time=$parent_start_time,	tunnel=$tunnel,	assoc_id=$assoc_id,	chunks=$chunks	chunks_sent=$chunks_sent	chunks_received=$chunks_received</code></p> </details> |
    | Threat Log (and WildFire Submissions Log) | <details> <summary><i> View Payload </i></summary> <p><code>timestamp=$receive_time, serial=$serial, type=$type, subtype=$subtype, time_generated=$time_generated, network.client.ip=$src, network.destination.ip=$dst, natsrc=$natsrc, natdst=$natdst, rule=$rule, usr.id=$srcuser, dstuser=$dstuser,	app=$app,	vsys=$vsys,	source_zone=$from,	destination_zone=$to,	inbound_if=$inbound_if,	outbound_if=$outbound_if,	logset=$logset,	sessionid=$sessionid,	repeatcnt=$repeatcnt,	network.client.port=$sport,	network.destination.port=$dport,	natsport=$natsport,	natdport=$natdport,	flags=$flags,	proto=$proto,	 evt.name=$action,	misc=$misc,	threatid=$threatid,	category=$category,	severity=$severity,	direction=$direction,	seqno=$seqno,	actionflags=$actionflags,	network.client.geoip.country.name=$srcloc,	dstloc=$dstloc,	contenttype=$contenttype,	pcap_id=$pcap_id,	filedigest=$filedigest,	cloud=$cloud,	url_idx=$url_idx,	http.useragent=$user_agent,	filetype=$filetype,	xff=$xff	referer=$referer,	sender=$sender,	subject=$subject,	recipient=$recipient,	reportid=$reportid,	vsys_name=$vsys_name,	device_name=$device_name,	src_uuid=$src_uuid,	dst_uuid=$dst_uuid,	http_method=$http_method,	tunnel_id=$tunnel_id, imsi=$imsi, monitortag=$monitortag, imei=$imei,	parent_session_id=$parent_session_id,	parent_start_time=$parent_start_time,	tunnel=$tunnel,	thr_category=$thr_category,	contentver=$contentver,	assoc_id=$assoc_id,	ppid=$ppid,	http_headers=$http_headers</code></p> </details> |
    | Authentication Log | <details> <summary><i> View Payload </i></summary> <p><code>timestamp=$time_generated, serial=$serial,	type=$type,	subtype=$subtype,	vsys=$vsys,	network.client.ip=$ip,	usr.id=$user,	normalize_user=$normalize_user,	object=$object,	authpolicy=$authpolicy,	repeatcnt=$repeatcnt,	authid=$authid,	vendor=$vendor	, logset=$logset, serverprofile=$serverprofile,	message=$message	,clienttype=$clienttype,	evt.outcome=$event,	factorno=$factorno,	seqno=$seqno,	actionflags=$actionflags, vsys_name=$vsys_name,	device_name=$device_name,	vsys_id=$vsys_id,	evt.name=$authproto</code></p> </details> |
    | HIP Match Log | <details> <summary><i> View Payload </i></summary> <p><code>timestamp=$time_generated, serial=$serial, type=$type, subtype=$subtype, time_generated=$time_generated,	usr.id=$srcuser, vsys=$vsys, machinename=$machinename, os=$os, network.client.ip=$src, matchname=$matchname, repeatcnt=$repeatcnt,	matchtype=$matchtype,	seqno=$seqno,	actionflags=$actionflags, vsys_name=$vsys_name,	device_name=$device_name,	vsys_id=$vsys_id,	srcipv6=$srcipv6,	hostid=$hostid</code></p> </details> |
    | User-ID Log | <details> <summary><i> View Payload </i></summary> <p><code>timestamp=$time_generated, serial=$serial, type=$type, subtype=$subtype, vsys=$vsys,	network.client.ip=$ip,	usr.id=$user, datasourcename=$datasourcename,	evt.name=$eventid,	repeatcnt=$repeatcnt, timeout=$timeout,	network.client.port=$beginport,	network.destination.port=$endport,	datasource=$datasource,	datasourcetype=$datasourcetype,	seqno=$seqno,	actionflags=$actionflags, vsys_name=$vsys_name,	device_name=$device_name,	vsys_id=$vsys_id,	factortype=$factortype,	factorcompletiontime=$factorcompletiontime,,	factorno=$factorno,	ugflags=$ugflags,	userbysource=$userbysource</code></p> </details> |
    | Tunnel Inspection Log | <details> <summary><i> View Payload </i></summary> <p><code>timestamp=$time_generated,	serial=$serial,	type=$type,	subtype=$subtype,	 network.client.ip=$src,	network.destination.ip=$dst,	natsrc=$natsrc,	natdst=$natdst,	rule=$rule,	usr.id=$srcuser,	dstuser=$dstuser,	app=$app,	vsys=$vsys,	source_zone=$from,	destination_zone=$to,	inbound_if=$inbound_if,	outbound_if=$outbound_if,	logset=$logset,	sessionid=$sessionid,	repeatcnt=$repeatcnt,	network.client.port=$sport,	network.destination.port=$dport,	natsport=$natsport,	natdport=$natdport,	flags=$flags,	proto=$proto,	evt.outcome=$action,	severity=$severity,	seqno=$seqno,	actionflags=$actionflags,	srcloc=$srcloc,	dstloc=$dstloc,	vsys_name=$vsys_name,	device_name=$device_name,	tunnelid=$tunnelid,	monitortag=$monitortag,	parent_session_id=$parent_session_id,	parent_start_time=$parent_start_time,	tunnel=$tunnel,	bytes=$bytes,	network.bytes_read=$bytes_sent,	network.bytes_written=$bytes_received,	packets=$packets,	pkts_sent=$pkts_sent,	pkts_received=$pkts_received,	max_encap=$max_encap,	unknown_proto=$unknown_proto,	strict_check=$strict_check,	tunnel_fragment=$tunnel_fragment,	sessions_created=$sessions_created,	sessions_closed=$sessions_closed,	session_end_reason=$session_end_reason,	evt.name=$action_source,	start=$start,	elapsed=$elapsed,	tunnel_insp_rule=$tunnel_insp_rule</code></p> </details> |
    | SCTP Log | <details> <summary><i> View Payload  </i></summary> <p><code>timestamp=$time_generated, serial=$serial, type=$type, network.client.ip=$src,	network.destination.ip=$dst, rule=$rule, vsys=$vsys, source_zone=$from, destination_zone=$to, inbound_if=$inbound_if, outbound_if=$outbound_if, logset=$logset, sessionid=$sessionid,	repeatcnt=$repeatcnt,	network.client.port=$sport,	network.destination.port=$dport,	proto=$proto,	action=$action, vsys_name=$vsys_name,	device_name=$device_name,	seqno=$seqno,	assoc_id=$assoc_id,	ppid=$ppid,	severity=$severity,	sctp_chunk_type=$sctp_chunk_type,	sctp_event_type=$sctp_event_type,	verif_tag_1=$verif_tag_1,	verif_tag_2=$verif_tag_2,	sctp_cause_code=$sctp_cause_code,	diam_app_id=$diam_app_id,	diam_cmd_code=$diam_cmd_code,	diam_avp_code=$diam_avp_code,	stream_id=$stream_id,	assoc_end_reason=$assoc_end_reason,	op_code=$op_code,	sccp_calling_ssn=$sccp_calling_ssn,	sccp_calling_gt=$sccp_calling_gt,	sctp_filter=$sctp_filter,	chunks=$chunks,	chunks_sent=$chunks_sent,	chunks_received=$chunks_received,	packets=$packets,	pkts_sent=$pkts_sent,	pkts_received=$pkts_received</code></p> </details> |
    | Config Log | <details> <summary><i> View Payload  </i></summary> <p><code>timestamp=$time_generated,	serial=$serial,	type=$type,	subtype=$subtype,	 network.client.ip=$host,	vsys=$vsys,	evt.name=$cmd,	usr.id=$admin,	client=$client,	evt.outcome=$result,	path=$path, before_change_detail=$before_change_detail,	after_change_detail=$after_change_detail,	seqno=$seqno,	actionflags=$actionflags, vsys_name=$vsys_name, device_name=$device_name</code></p> </details> |
    | System Log | <details> <summary><i> View Payload </i></summary> <p><code>timestamp=$time_generated, serial=$serial, type=$type, subtype=$subtype,	vsys=$vsys,	evt.name=$eventid,	object=$object,	module=$module,	severity=$severity,	opaque=$opaque,	seqno=$seqno, actionflags=$actionflags, vsys_name=$vsys_name, device_name=$device_name</code></p> </details> |
    | Correlated Events Log | <details> <summary><i> View Payload </i></summary> <p><code>timestamp=$time_generated, serial=$serial, type=$type, subtype=$subtype,	vsys=$vsys,	evt.name=$eventid,	object=$object,	module=$module,	severity=$severity,	opaque=$opaque,	seqno=$seqno, actionflags=$actionflags, vsys_name=$vsys_name,	device_name=$device_name</code></p> </details> |
    | GTP Log  | <details> <summary><i> View Payload </i></summary> <p><code>timestamp=$start, serial=$serial, type=$type, subtype=$subtype,	network.client.ip=$src,	network.destination.ip=$dst, rule=$rule, app=$app, vsys=$vsys,	source_zone=$from,	destination_zone=$to,	inbound_if=$inbound_if,	outbound_if=$outbound_if, logset=$logset,	sessionid=$sessionid,	network.client.port=$sport,	network.destination.port=$dport, proto=$proto,	evt.name=$action,	event_type=$event_type,	msisdn=$msisdn,	apn=$apn,	rat=$rat,	msg_type=$msg_type,	end_ip_adr=$end_ip_adr,	teid1=$teid1,	teid2=$teid2,	gtp_interface=$gtp_interface,	cause_code=$cause_code,	severity=$severity,	mcc=$mcc,	mnc=$mnc,	area_code=$area_code,	cell_id=$cell_id,	event_code=$event_code,	srcloc=$srcloc,	dstloc=$dstloc,	imsi=$imsi,	imei=$imei,	start=$start,	elapsed=$elapsed,	tunnel_insp_rule=$tunnel_insp_rule</code></p> </details> |
    | Data Filtering Log | <details> <summary><i> View Payload </i></summary> <p><code>timestamp=$receive_time, serial=$serial, type=$type, subtype=$subtype, time_generated=$time_generated, network.client.ip=$src, network.destination.ip=$dst, natsrc=$natsrc, natdst=$natdst, rule=$rule, usr.id=$srcuser, dstuser=$dstuser, app=$app, vsys=$vsys, source_zone=$from, destination_zone=$to, inbound_if=$inbound_if, outbound_if=$outbound_if, logset=$logset, sessionid=$sessionid, repeatcnt=$repeatcnt, network.client.port=$sport, network.destination.port=$dport, natsport=$natsport, natdport=$natdport, flags=$flags, proto=$proto, evt.name=$action, misc=$misc, threatid=$threatid, category=$category, severity=$severity, direction=$direction, seqno=$seqno, actionflags=$actionflags, network.client.geoip.country.name=$srcloc, dstloc=$dstloc, contenttype=$contenttype, pcap_id=$pcap_id, filedigest=$filedigest, cloud=$cloud, url_idx=$url_idx, http.useragent=$user_agent, filetype=$filetype, xff=$xff, referer=$referer, sender=$sender, subject=$subject, recipient=$recipient, reportid=$reportid, vsys_name=$vsys_name, device_name=$device_name, src_uuid=$src_uuid, dst_uuid=$dst_uuid, http_method=$http_method, tunnel_id=$tunnel_id, imsi=$imsi, monitortag=$monitortag, imei=$imei, parent_session_id=$parent_session_id, parent_start_time=$parent_start_time, tunnel=$tunnel, thr_category=$thr_category, contentver=$contentver, assoc_id=$assoc_id, ppid=$ppid, http_headers=$http_headers, url_category_list=$url_category_list, rule_uuid=$rule_uuid, http2_connection=$http2_connection, dynusergroup_name=$dynusergroup_name, xff_ip=$xff_ip, src_osfamily=$src_osfamily, src_osversion=$src_osversion, src_host=$src_host, src_mac=$src_mac, dst_osfamily=$dst_osfamily, dst_osversion=$dst_osversion, dst_host=$dst_host, dst_mac=$dst_mac, container_id=$container_id, pod_namespace=$pod_namespace, pod_name=$pod_name, src_edl=$src_edl, dst_edl=$dst_edl, hostid=$hostid, serialnumber=$serialnumber, domain_edl=$domain_edl, src_dag=$src_dag, dst_dag=$dst_dag, partial_hash=$partial_hash, high_res_timestamp=$high_res_timestamp, reason=$reason, justification=$justification</code></p> </details> |
    | URL Filtering Log | <details> <summary><i> View Payload </i></summary> <p><code>timestamp=$receive_time, serial=$serial, type=$type, subtype=$subtype, time_generated=$time_generated, network.client.ip=$src, network.destination.ip=$dst, natsrc=$natsrc, natdst=$natdst, rule=$rule, usr.id=$srcuser, dstuser=$dstuser, app=$app, vsys=$vsys, source_zone=$from, destination_zone=$to, inbound_if=$inbound_if, outbound_if=$outbound_if, logset=$logset, sessionid=$sessionid, repeatcnt=$repeatcnt, network.client.port=$sport, network.destination.port=$dport, natsport=$natsport, natdport=$natdport, flags=$flags, proto=$proto, evt.name=$action, misc=$misc, threatid=$threatid, category=$category, severity=$severity, direction=$direction, seqno=$seqno, actionflags=$actionflags, network.client.geoip.country.name=$srcloc, dstloc=$dstloc, contenttype=$contenttype, pcap_id=$pcap_id, filedigest=$filedigest, cloud=$cloud, url_idx=$url_idx, http.useragent=$user_agent, filetype=$filetype, xff=$xff, referer=$referer, sender=$sender, subject=$subject, recipient=$recipient, reportid=$reportid, vsys_name=$vsys_name, device_name=$device_name, src_uuid=$src_uuid, dst_uuid=$dst_uuid, http_method=$http_method, tunnel_id=$tunnel_id, imsi=$imsi, monitortag=$monitortag, imei=$imei, parent_session_id=$parent_session_id, parent_start_time=$parent_start_time, tunnel=$tunnel, thr_category=$thr_category, contentver=$contentver, assoc_id=$assoc_id, ppid=$ppid, http_headers=$http_headers, url_category_list=$url_category_list, rule_uuid=$rule_uuid, http2_connection=$http2_connection, dynusergroup_name=$dynusergroup_name, xff_ip=$xff_ip, src_osfamily=$src_osfamily, src_osversion=$src_osversion, src_host=$src_host, src_mac=$src_mac, dst_osfamily=$dst_osfamily, dst_osversion=$dst_osversion, dst_host=$dst_host, dst_mac=$dst_mac, container_id=$container_id, pod_namespace=$pod_namespace, pod_name=$pod_name, src_edl=$src_edl, dst_edl=$dst_edl, hostid=$hostid, serialnumber=$serialnumber, domain_edl=$domain_edl, src_dag=$src_dag, dst_dag=$dst_dag, partial_hash=$partial_hash, high_res_timestamp=$high_res_timestamp, reason=$reason, justification=$justification</code></p> </details> |
    | GlobalProtect Log | <details> <summary><i> View Payload </i></summary> <p><code>timestamp=$receive_time, serial=$serial, type=$type, subtype=$subtype, time_generated=$time_generated, vsys=$vsys, evt.name=$eventid, stage=$stage, auth_method=$auth_method, tunnel_type=$tunnel_type, usr.id=$srcuser, srcregion=$srcregion, machinename=$machinename, public_ip=$public_ip, public_ipv6=$public_ipv6, private_ip=$private_ip, private_ipv6=$private_ipv6, hostid=$hostid, serialnumber=$serialnumber, client_ver=$client_ver, client_os=$client_os, client_os_ver=$client_os_ver, repeatcnt=$repeatcnt, reason=$reason, error=$error, opaque=$opaque, status=$status, location=$location, login_duration=$login_duration, connect_method=$connect_method, error_code=$error_code, portal=$portal, seqno=$seqno, actionflags=$actionflags, selection_type=$selection_type, response_time=$response_time, priority=$priority, attempted_gateways=$attempted_gateways, gateway=$gateway, dg_hier_level_1=$dg_hier_level_1, dg_hier_level_2=$dg_hier_level_2, dg_hier_level_3=$dg_hier_level_3, dg_hier_level_4=$dg_hier_level_4, vsys_name=$vsys_name, device_name=$device_name, vsys_id=$vsys_id</code></p> </details> |

5. Go to **Objects > Log Forwarding**, and add a log forwarding profile that sends the required log types to the syslog server profile.
6. [Restart the Agent][5].

### Events

The Palo Alto Networks Firewall integration does not include any events.

### Service Checks

The Palo Alto Networks Firewall integration does not include any service checks.

## Troubleshooting

Need help? Contact [Datadog support][10].

[1]: https://www.paloaltonetworks.com/network-security/next-generation-firewall
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[4]: https://github.com/DataDog/integrations-core/blob/master/pan_firewall/datadog_checks/pan_firewall/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/integrations-core/blob/master/pan_firewall/metadata.csv
[8]: https://docs.paloaltonetworks.com/pan-os/11-1/pan-os-admin/monitoring/use-syslog-for-monitoring/configure-syslog-monitoring
[9]: https://docs.paloaltonetworks.com/pan-os/10-1/pan-os-admin/monitoring/use-syslog-for-monitoring/syslog-field-descriptions
[10]: https://docs.datadoghq.com/help/
