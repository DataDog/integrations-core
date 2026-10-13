# Palo Alto Networks Firewall Log Integration

## Overview

Datadog's Palo Alto Networks Firewall Log integration allows customers to ingest, parse, and analyze Palo Alto Networks firewall logs. This log integration relies on the HTTPS log templating and forwarding capability provided by PAN OS, the operating system that runs in Palo Alto firewalls. PAN-OS allows customers to forward threat, traffic, authentication, and other important log events.

The integration also collects metrics and Network Device Monitoring (NDM) device metadata from the PAN-OS XML API, either directly from each firewall or through Panorama discovery. The metrics cover system resources, interfaces, tunnels, routing, licenses, security rules, threat counts, and optional global counters and top-N reports. The firewalls appear in NDM with their serial number as device ID. If you also monitor the same firewalls with SNMP, they appear as separate devices, because the two sources use different device IDs.

### Key use cases
#### Respond to high severity threat events
Firewall threat logs provide context on threats detected by a firewall, which can be filtered and analyzed by severity, type, origin IPs/countries, and more.

#### Make informed decisions on Firewall deployment
Firewall traffic logs can be used to measure the traffic and sessions passing through a firewall and also gives you the ability to monitor for anomalous throughput across firewall deployment.

#### Monitor firewall health and capacity
Resource, interface, tunnel, and license metrics show a firewall running out of capacity or a tunnel or routing peer going down, and threat counts by severity and action give you a metric view alongside the logs.

#### Monitor authentication anomalies
Firewall authentication logs provide detailed information on users as they authenticate with Palo Alto Networks firewall. These logs can be used to monitor anomalous spikes in authentication traffic from specific protocols, users, locations, and more.

**Minimum Agent version:** 7.31.1

## Setup

### Metrics and NDM collection

The `pan_firewall` check polls the PAN-OS XML API of each firewall, either from a static list of firewalls or from the firewalls that a Panorama server manages. Metrics collection is independent of log collection: you can configure either one or both.

#### Create an admin role and account

1. In PAN-OS, go to **Device > Admin Roles** and add a role profile with an **XML API** tab that allows **Operational Requests**, **Report**, and **Log**. All other XML API privileges and the Web UI, Command Line, and REST API tabs can stay disabled.
2. Go to **Device > Administrators** and add an account that uses this role, with a password or an API key.
3. Commit the changes.

For Panorama discovery, create an admin role on Panorama that allows **Operational Requests** in the XML API tab. The Agent does not poll the discovered firewalls with the Panorama credentials. It polls each one with the `firewall_credentials` entry that matches the polled IP address, so those accounts need the role described above.

#### Network reach

The Agent connects to the management interface of each firewall over HTTPS (port 443 by default). Make sure that:

- The management interface (or the interface that carries management traffic) has HTTPS enabled in its management profile.
- If you restrict management access, the Agent host is in the **Permitted IP Addresses** list (`permitted-ip`) of the firewall, and in the admin role or account restrictions, if you use any.

With Panorama discovery, the Agent must also reach the firewall IP addresses that Panorama reports, or the addresses you set in `firewall_ip_overrides`. Firewalls that Panorama shows as disconnected (`connected=no`) are not polled.

#### TLS

PAN-OS management interfaces ship with a self-signed certificate. Either install a certificate signed by a CA that the Agent trusts (and set `tls_ca_cert` for a private CA), or set `tls_verify: false` to accept the self-signed certificate. TLS settings apply to the whole instance. Put firewalls with a different certificate setup in a separate instance.

#### Configuration

Create a `pan_firewall.d/conf.yaml` file at the root of the [Agent's configuration directory][3]. See the [sample `pan_firewall.d/conf.yaml`][11] for all available options, then [restart the Agent][4].

Static list of firewalls with one account:

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

Static list of firewalls with different credentials by network. The Agent uses the first entry whose `cidr` contains the firewall IP, and an entry without `cidr` matches every firewall:

```yaml
init_config:

instances:
  - firewalls:
      - 192.0.2.10
      - 198.51.100.20
    firewall_credentials:
      - cidr: 192.0.2.0/24
        username: <USERNAME>
        password: <PASSWORD>
      - cidr: 198.51.100.0/24
        api_key: <API_KEY>
    tls_verify: false
```

Panorama discovery. Quote the serial numbers in `firewall_ip_overrides`: an unquoted serial can be read by YAML as a number, and the Agent then matches it by numeric value and logs a warning.

```yaml
init_config:

instances:
  - panorama_host: panorama.example.com
    panorama_api_key: <PANORAMA_API_KEY>
    firewall_ips:
      include:
        - 192.0.2.0/24
    firewall_ip_overrides:
      "012345678901": 192.0.2.30
    firewall_credentials:
      - username: <USERNAME>
        password: <PASSWORD>
    tls_verify: false
```

#### Namespace

Set `namespace` to keep the device IDs of firewalls in overlapping address spaces apart in NDM. The default is `default`. Use the same namespace as your other NDM sources only if the devices should be correlated.

#### API budget

Each firewall receives about 265 API requests per hour with the default options, and about 355 with every optional collector enabled (`collect_global_counters`, `collect_ospf`, and `collect_reports`). The Agent keeps at most 2 requests in flight per firewall. Each call runs on its own interval, from 2 minutes to 24 hours, so a `min_collection_interval` below the default of 60 seconds does not collect more data. A first run with all collectors enabled took about 30 seconds per firewall in the lab.

#### Commit skipping

While a commit or a content update (Commit, AutoCom, Content, Antivirus, or WildFire job) is running or queued on a firewall, the Agent skips collection for that firewall and resumes on the next run after the job ends. Skipping is capped at 10 minutes: if a job is still running after that, the Agent collects anyway and logs a warning.

### Log collection

 1. [Install the Datadog Agent][1] on a machine that is reachable by the firewall and can connect to the internet. Confirm that log collection is enabled. To enable log collection, change `logs_enabled: false` to `logs_enabled: true` in your Agent's main configuration file (datadog.yaml). See the [Host Agent Log collection documentation][10] for more information and examples.
 2. In PanOS, Select Device >> Server Profiles >> Syslog , add a name for the server profile. Follow the Syslog log forwarding [configuration steps][2]. Same steps listed below.
 3. Click Add and provide the following details of the server:
 	* Name of the server
 	* IP address of the machine with datadog agent
 	* Transport as TCP
 	* Port as 10518 and format as BSD
 4. Copy and configure custom log format for the required log type. The formats below are mappings from the formats listed in [the Palo Alto Networks Syslog Field Descriptions docs][8].

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

 5. Click OK, this creates a syslog server profile.
 6. Click on the Objects tab, this opens the log forwarding profile screen.
 7. Create log forwarding profile by providing the name, log type and syslog profile
 8. Create a pan.firewall.d/conf.yaml file at the root of the [Agent's configuration directory][3] with the below content.

     ```yaml
     logs:
     - type: tcp
       port: 10518
       service: "firewall"
       source: "pan.firewall"
     ```
 9. [Restart Agent][4].

## Data Collected

### Metrics

See [metadata.csv][12] for the list of metrics that the `pan_firewall` check collects, with their types and tags. Every metric carries the `device_vendor:paloaltonetworks` tag and tags that identify the firewall by serial number and IP address.

Counters such as `pan_firewall.counter.global` and `pan_firewall.security_rule.hits` are monotonic counts. The Agent needs two samples to report the first value, so they appear 3 to 6 minutes after it starts. Gauges appear on the first run of their collector.

#### Global counters

With `collect_global_counters: true`, the check collects 26 PAN-OS global counters. Each one is sent as `pan_firewall.counter.global` with its counter name, category, and aspect as tags, and a counter that the firewall does not list is sent as 0. The check also sums the counters that PAN-OS classifies as drops into a per-aspect dropped packet metric.

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

#### Reports

With `collect_reports: true`, the check runs 10 top-N reports every 30 minutes and keeps the top `report_top_n` entries (10 by default) of each. These are custom dynamic reports over the last 24 hours. The Agent drops a report job that is still running after it carried the job over 3 times, and submits the next report:

- Top applications
- Top application categories
- Top technology categories
- Top sources
- Top destinations
- Top source countries
- Top destination countries
- Top ingress zones
- Top egress zones
- Top security rules

#### Threat counts

`pan_firewall.threat.count` is a count of the threat logs that the firewall wrote since the previous successful query, grouped by severity, action, subtype, and virtual system. The check runs every 5 minutes and reads logs by sequence number, not by time, so each log is counted once, including across Agent restarts and large bursts, and a firewall clock change has no effect. The first run counts nothing and sets the starting point at the newest log.

### Logs

The PANOS integration collects logs from the Palo Alto Networks firewall integration and forwards them to Datadog.

### Events

The PANOS integration does not send any events.

### Service Checks

The PANOS integration does not include any service checks.

## Further Reading

Additional helpful documentation, links, and articles:

- [Log types and fields][5]
- [Logs Collection documentation][6]

## Limitations

- The VM-Series reports no power or temperature sensors and no interface speed. Hardware firewalls report them, but these parsers are verified on synthetic data only until a hardware capture is available.
- On a firewall in an HA pair the HA state is reported on the device metadata, but the HA link counters (`ha.interface.*`) are not collected yet; the integration logs one warning.
- BGP and OSPF metrics require the legacy routing engine. Firewalls running the Advanced Routing Engine (ARE) log one warning and report no BGP or OSPF metrics.
- Administrative status and interface description come from SNMP; the XML API does not provide them.
- The Top HTTP Applications report is not available.
- `device_id` is the firewall serial number, so a firewall does not merge with an SNMP record for the same device.
- A virtual system with no interfaces is not detected automatically; list it in `vsys`.
- If a reboot or an HA failover resets the threat log sequence number, up to about 35 minutes of threat logs may not be counted.
- TLS settings apply per instance. Put firewalls with a different certificate setup in a separate instance.
- Perpetual licenses report `license.expired` as 0 and no `license.days_left`.
- Panorama discovery was tested live against Panorama 11.2.15 managing 2 VM-Series firewalls. Panorama-managed HA pairs and firewalls behind NAT were not tested.

## Troubleshooting

- If `pan_firewall.api.authentication.status` is 1, the firewall rejected the credentials or the API key. Check the account, its admin role (**Operational Requests**, **Report**, and **Log**), and the `permitted-ip` list.
- If you already collect logs with a `pan.firewall.d/conf.yaml` file, you can keep it as it is. The `pan_firewall` check and log collection are configured separately.

Need help? Contact [Datadog support][7].

[1]: /account/settings/agent/latest
[2]: https://www.youtube.com/watch?v=LOPXg0oCMPs
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6v7
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.paloaltonetworks.com/pan-os/9-1/pan-os-admin/monitoring/use-syslog-for-monitoring/syslog-field-descriptions
[6]: https://docs.datadoghq.com/logs/log_collection/?tab=tailexistingfiles#getting-started-with-the-agent
[7]: https://docs.datadoghq.com/help/
[8]: https://docs.paloaltonetworks.com/pan-os/10-1/pan-os-admin/monitoring/use-syslog-for-monitoring/syslog-field-descriptions
[10]: https://docs.datadoghq.com/agent/logs/
[11]: https://github.com/DataDog/integrations-core/blob/master/pan_firewall/datadog_checks/pan_firewall/data/conf.yaml.example
[12]: https://github.com/DataDog/integrations-core/blob/master/pan_firewall/metadata.csv

