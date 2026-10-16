# Agent Check: Palo Alto Networks Firewall

## Overview

This check monitors [Palo Alto Networks firewalls][1] through the Datadog Agent.

Palo Alto Networks next-generation firewalls run PAN-OS and enforce security policy, threat prevention, and VPN connectivity at the network edge and in the data center. This integration polls the PAN-OS XML API of each firewall, either from a static list or from the firewalls that a Panorama server manages, and reports their metrics and device metadata to Network Device Monitoring (NDM). It also parses the threat, traffic, authentication, and other logs that PAN-OS forwards through syslog.

### What this integration monitors

- **System resources**: Management plane CPU, memory, swap, and disk usage, data plane CPU utilization, and, on hardware firewalls, power and temperature sensors.
- **Interfaces and tunnels**: Traffic, errors, drops, and attack counters per interface, and the state and traffic of IPsec tunnels.
- **Routing**: BGP peer state and prefix counts, and OSPF neighbor state, to detect a routing peer going down.
- **Licenses**: Expiration status and days left for each subscription.
- **Security rules and threats**: Hit counts per security rule, and threat counts by severity, action, and subtype alongside the threat logs.
- **Global counters and reports** (optional): PAN-OS global counters, dropped packets by aspect, and top-N reports for applications, sources, destinations, zones, and rules.
- **Logs**: Threat, traffic, authentication, User-ID, GlobalProtect, configuration, system, and other PAN-OS log types, parsed for filtering by severity, origin, user, and more.

**Minimum Agent version:** 7.31.1

## Setup

Follow the instructions below to install and configure this check for an Agent running on a host. For containerized environments, see the [Autodiscovery Integration Templates][2] for guidance on applying these instructions.

### Installation

The Palo Alto Networks Firewall check is included in the [Datadog Agent][3] package. No additional installation is needed on your server.

### Configuration

#### Metric collection

1. Create an account for the Agent on each firewall:
   1. In PAN-OS, go to **Device > Admin Roles** and add a role profile with an **XML API** tab that allows **Operational Requests**, **Report**, and **Log**. All other privileges can stay disabled.
   2. Go to **Device > Administrators** and add an account that uses this role, with a password or an API key.
   3. Commit the changes.

   For Panorama discovery, also create an account on Panorama with a role that allows **Operational Requests** in the XML API tab. The Agent uses it only to list the managed firewalls, and polls each firewall with the matching `firewall_credentials` entry.

2. Make sure the Agent can reach the management interface of each firewall over HTTPS (port 443). HTTPS must be enabled in the management profile of that interface, and if you restrict management access, the Agent host must be in the **Permitted IP Addresses** list. With Panorama discovery, the Agent polls each firewall at the IP address that Panorama reports for it.

3. Edit the `pan_firewall.d/conf.yaml` file, in the `conf.d/` folder at the root of your [Agent's configuration directory][4], to start collecting your Palo Alto Networks firewall data. See the [sample pan_firewall.d/conf.yaml][5] for all available configuration options. For example:

   Static list of firewalls:

   ```yaml
   init_config:

   instances:
     - firewalls:
         - 192.0.2.10
         - 192.0.2.11
       firewall_credentials:
         - username: <USERNAME>
           password: <PASSWORD>
       tls_verify: false
   ```

   Panorama discovery:

   ```yaml
   init_config:

   instances:
     - panorama_host: panorama.example.com
       panorama_api_key: <PANORAMA_API_KEY>
       firewall_ips:
         include:
           - 192.0.2.0/24
       firewall_credentials:
         - username: <USERNAME>
           password: <PASSWORD>
       tls_verify: false
   ```

   **Note**: The Agent uses the first `firewall_credentials` entry whose `cidr` contains the firewall IP, and an entry without `cidr` matches every firewall. Add one entry per network when firewalls use different accounts.

   **Note**: PAN-OS management interfaces ship with a self-signed certificate. Either install a certificate signed by a CA that the Agent trusts (and set `tls_ca_cert` for a private CA), or set `tls_verify: false`. TLS settings apply to the whole instance, so put firewalls with a different certificate setup in a separate instance.

4. [Restart the Agent][6].

#### Log collection

1. Enable log collection in your `datadog.yaml` file:

    ```yaml
    logs_enabled: true
    ```

2. Edit the logs configuration block in your `pan_firewall.d/conf.yaml` file. For example:

    ```yaml
    logs:
      - type: tcp
        port: 10518
        service: firewall
        source: pan.firewall
    ```

3. In PAN-OS, go to **Device > Server Profiles > Syslog** and add a server profile. See the [PAN-OS syslog forwarding documentation][7] for details. Add a server with:
   - The IP address of the Agent host
   - Transport **TCP**, port **10518**, and format **BSD**

4. In the **Custom Log Format** tab, configure the format for each log type you want to collect. The formats below map the fields listed in the [PAN-OS syslog field descriptions][8].

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

5. Click **OK** to save the syslog server profile.

6. Go to **Objects > Log Forwarding**, and add a log forwarding profile that sends the required log types to the syslog server profile.

7. [Restart the Agent][6].

### Validation

[Run the Agent's status subcommand][9] and look for `pan_firewall` under the Checks section.

## Data Collected

### Metrics

See [metadata.csv][10] for a list of metrics provided by this integration. Every metric carries the `device_vendor:paloaltonetworks` tag and tags that identify the firewall by serial number and IP address.

With `collect_global_counters: true`, the check collects the following PAN-OS global counters as `pan_firewall.counter.global`, tagged by counter name, category, and aspect:

| Counter | Description |
| ------- | ----------- |
| `appid_unknown_fini_empty` | The number of unknown applications because of no data |
| `flow_arp_pkt_rcv` | ARP packets received |
| `flow_arp_pkt_xmt` | ARP packets transmitted |
| `flow_arp_rcv_err` | ARP receive error |
| `flow_arp_resolve_xmt` | ARP resolution packets transmitted |
| `flow_fwd_l3_mcast_drop` | Packets dropped: no route for IP multicast |
| `flow_fwd_l3_noarp` | Packets dropped: no ARP |
| `flow_host_ha_decap_err` | Packets dropped: decapsulation error from control plane's HA agent |
| `flow_host_service_allow` | Device management session allowed |
| `flow_host_service_deny` | Device management session denied |
| `flow_ipv6_disabled` | Packets dropped: IPv6 disabled on interface |
| `flow_lion_rcv_err` | Packets dropped: receive error from offload processor |
| `flow_mld_pkt_rcv` | MLD packets received |
| `flow_mld_pkt_xmt` | MLD packets transmitted |
| `flow_no_interface` | Packets dropped: invalid interface |
| `flow_rcv_dot1q_tag_err` | Packets dropped: 802.1q tag not configured |
| `flow_rcv_err` | Packets dropped: flow stage receive error |
| `pkt_alloc` | Packets allocated |
| `pkt_recv` | Packets received |
| `pkt_recv_zero` | Packets received from QoS 0 |
| `pkt_sent` | Packets transmitted |
| `session_freed` | Sessions freed |
| `session_install_error` | Sessions installation error |
| `session_installed` | Sessions installed |
| `session_peer_not_close` | Installation flow close error |
| `ssl_hsm_up_down_event_rcv` | The number of HSM up/down events received |

With `collect_reports: true`, the check runs top-N reports over the last 24 hours every 30 minutes, and keeps the top `report_top_n` entries of each.

### Logs

The Palo Alto Networks Firewall integration collects the logs that PAN-OS forwards through syslog. See [Log collection](#log-collection) to configure it.

### Events

The Palo Alto Networks Firewall integration does not include any events.

### Service Checks

The Palo Alto Networks Firewall integration does not include any service checks.

## Troubleshooting

### Authentication failures

If `pan_firewall.api.authentication.status` is `1`, the firewall rejected the credentials or the API key. Check the account, its admin role (**Operational Requests**, **Report**, and **Log**), and the **Permitted IP Addresses** list.

### Counter metrics missing after the Agent starts

Counters such as `pan_firewall.counter.global` and `pan_firewall.security_rule.hits` are monotonic counts. The Agent needs two samples to report the first value, so they appear 3 to 6 minutes after it starts.

### No collection while a commit is running

While a commit or a content update is running or queued on a firewall, the Agent skips collection for that firewall and resumes after the job ends. If the job is still running after 10 minutes, the Agent collects anyway and logs a warning.

### Firewalls not reachable at their Panorama-reported IP address

The Agent does not poll firewalls that Panorama shows as disconnected. If the Agent can't reach the IP address that Panorama reports for a firewall (for example, behind NAT), add it to the `firewall_ips` exclude list of the Panorama instance, and poll it from a separate instance that lists its reachable IP address in `firewalls`.

### Firewalls appear twice in NDM

The integration uses the firewall serial number as the NDM device ID. If you also monitor the same firewalls with SNMP, they appear as separate devices. Set `namespace` to keep firewalls in overlapping address spaces apart.

### Missing metrics

- BGP and OSPF metrics require the legacy routing engine. Firewalls that run the Advanced Routing Engine (ARE) report no BGP or OSPF metrics, and the Agent logs a warning.
- On a firewall in an HA pair, the HA state is reported on the device metadata, but the HA link counters are not collected.
- VM-Series firewalls report no power or temperature sensors and no interface speed.
- Perpetual licenses report `pan_firewall.license.expired` as `0` and no `pan_firewall.license.days_left`.
- A virtual system with no interfaces is not detected automatically. List it in `vsys`.
- If a reboot or an HA failover resets the threat log sequence number, up to about 35 minutes of threat logs may not be counted in `pan_firewall.threat.count`.

### Existing log configuration

If you already collect logs with a `pan.firewall.d/conf.yaml` file, you can keep it as it is. The `pan_firewall` check and log collection are configured separately.

Need help? Contact [Datadog support][11].

## Further Reading

Additional helpful documentation, links, and articles:

- [PAN-OS syslog field descriptions][8]
- [Log collection documentation][12]

[1]: https://www.paloaltonetworks.com/network-security/next-generation-firewall
[2]: https://docs.datadoghq.com/containers/kubernetes/integrations/
[3]: https://app.datadoghq.com/account/settings/agent/latest
[4]: https://docs.datadoghq.com/agent/configuration/agent-configuration-files/
[5]: https://github.com/DataDog/integrations-core/blob/master/pan_firewall/datadog_checks/pan_firewall/data/conf.yaml.example
[6]: https://docs.datadoghq.com/agent/configuration/agent-commands/#start-stop-and-restart-the-agent
[7]: https://docs.paloaltonetworks.com/pan-os/11-1/pan-os-admin/monitoring/use-syslog-for-monitoring/configure-syslog-monitoring
[8]: https://docs.paloaltonetworks.com/pan-os/10-1/pan-os-admin/monitoring/use-syslog-for-monitoring/syslog-field-descriptions
[9]: https://docs.datadoghq.com/agent/configuration/agent-commands/#agent-status-and-information
[10]: https://github.com/DataDog/integrations-core/blob/master/pan_firewall/metadata.csv
[11]: https://docs.datadoghq.com/help/
[12]: https://docs.datadoghq.com/logs/log_collection/
