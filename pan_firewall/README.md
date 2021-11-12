# Palo Alto Networks Firewall Log Integration

## Overview

Datadog's Palo Alto Networks Firewall Log integration allows customers to ingest, parse and analyze Palo Alto Networks firewall logs. This log integration relies on the HTTPS log templating and forwarding capability provided by PAN OS, the operating system that runs in Palo Alto firewalls. PAN-OS allows customers to forward threat, traffic, authentication, and other important log events.

### Key use cases
#### Respond to high severity threat events
Firewall threat logs provide rich context on threats detected by a firewall, which can be filtered and analyzed by severity, type, origin IPs/countries, and more. 

#### Make informed decisions on Firewall deployment
Firewall traffic logs can be used to measure the traffic and sessions passing through a firewall and also gives you the ability to monitor for anomalous throughput across firewall deployment.

#### Monitor authentication anomalies
Firewall authentication logs provide detailed information on users as they authenticate with Palo Alto Networks firewall. These logs can be used to monitor anomalous spikes in authentication traffic from specific protocols, users, locations, and more.

## Setup

### Log collection 

 1. [Install the Datadog Agent][1] on a machine that is reachable by the firewall and can connect to the internet.
 2. In PanOS, Select Device >> Server Profiles >> Syslog , add a name for the server profile. Follow the Syslog log forwarding [configuration steps][2]. Same steps listed below.
 3. Click Add and provide the following details of the server:
 	* Name of the server
 	* IP address of the machine with datadog agent 
 	* Transport as TCP
 	* Port as 10518 and format as BSD
 4. Copy and configure custom log format for the required log type.

    | Name     	                   | Format                                                |
    | -------------------------------| ---------------------------------------------------------- |
    | Traffic Log | <details> <summary><i> View Payload </i> </summary> <p>  timestamp=$time_generated, serial=$serial, type=$type, subtype=$subtype, time_generated=$time_generated, network.client.ip=$src, network.destination.ip=$dst, natsrc=$natsrc, natdst=$natdst, rule=$rule, usr.id=$srcuser, dstuser=$dstuser,	app=$app,	vsys=$vsys,	from=$from,	to=$to,	inbound_if=$inbound_if,	outbound_if=$outbound_if,	logset=$logset,	sessionid=$sessionid,	repeatcnt=$repeatcnt,	network.client.port=$sport,	network.destination.port=$dport, natsport=$natsport	natdport=$natdport,	flags=$flags,	proto=$proto,	 evt.name=$action,	bytes=$bytes,	network.bytes_read=$bytes_sent,	network.bytes_written=$bytes_received, start=$start, elapsed=$elapsed, category=$category,	seqno=$seqno,	actionflags=$actionflags,	network.client.geoip.country.name=$srcloc,	dstloc=$dstloc,	pkts_sent=$pkts_sent, pkts_received=$pkts_received, session_end_reason=$session_end_reason,	device_name=$device_name,	action_source=$action_source,	src_uuid=$src_uuid,	dst_uuid=$dst_uuid,	tunnelid=$tunnelid,  imsi= $imsi, monitortag=$monitortag, imei=$imei,	parent_session_id=$parent_session_id,	parent_start_time=$parent_start_time,	tunnel=$tunnel,	assoc_id=$assoc_id,	chunks=$chunks	chunks_sent=$chunks_sent	chunks_received=$chunks_received </p> </details> |
    | Threat Log | <details> <summary><i> View Payload </i></summary> <p> timestamp=$receive_time, serial=$serial, type=$type, subtype=$subtype, time_generated=$time_generated, network.client.ip=$src, network.destination.ip=$dst, natsrc=$natsrc, natdst=$natdst, rule=$rule, usr.id=$srcuser, dstuser=$dstuser,	app=$app,	vsys=$vsys,	from=$from,	to=$to,	inbound_if=$inbound_if,	outbound_if=$outbound_if,	logset=$logset,	sessionid=$sessionid,	repeatcnt=$repeatcnt,	network.client.port=$sport,	network.destination.port=$dport,	natsport=$natsport,	natdport=$natdport,	flags=$flags,	proto=$proto,	 evt.name=$action,	misc=$misc,	threatid=$threatid,	category=$category,	severity=$severity,	direction=$direction,	seqno=$seqno,	actionflags=$actionflags,	network.client.geoip.country.name=$srcloc,	dstloc=$dstloc,	contenttype=$contenttype,	pcap_id=$pcap_id,	filedigest=$filedigest,	cloud=$cloud,	url_idx=$url_idx,	http.useragent=$user_agent,	filetype=$filetype,	xff=$xff	referer=$referer,	sender=$sender,	subject=$subject,	recipient=$recipient,	reportid=$reportid,	vsys_name=$vsys_name,	device_name=$device_name,	src_uuid=$src_uuid,	dst_uuid=$dst_uuid,	http_method=$http_method,	tunnel_id=$tunnel_id, imsi=$imsi, monitortag=$monitortag, imei=$imei,	parent_session_id=$parent_session_id,	parent_start_time=$parent_start_time,	tunnel=$tunnel,	thr_category=$thr_category,	contentver=$contentver,	assoc_id=$assoc_id,	ppid=$ppid,	http_headers=$http_headers  </p> </details> |
    | Authentication Log | <details> <summary><i> View Payload </i></summary> <p>  timestamp=$time_generated, serial=$serial,	type=$type,	subtype=$subtype,	vsys=$vsys,	network.client.ip=$ip,	usr.id=$user,	normalize_user=$normalize_user,	object=$object,	authpolicy=$authpolicy,	repeatcnt=$repeatcnt,	authid=$authid,	vendor=$vendor	, logset=$logset, serverprofile=$serverprofile,	message=$message	,clienttype=$clienttype,	evt.outcome=$event,	factorno=$factorno,	seqno=$seqno,	actionflags=$actionflags, vsys_name=$vsys_name,	device_name=$device_name,	vsys_id=$vsys_id,	evt.name=$authproto  </p> </details> |
    | HIP Match Log | <details> <summary><i> View Payload </i></summary> <p> timestamp=$time_generated, serial=$serial, type=$type, subtype=$subtype, time_generated=$time_generated,	usr.id=$srcuser, vsys=$vsys, machinename=$machinename, os=$os, network.client.ip=$src, matchname=$matchname, repeatcnt=$repeatcnt,	matchtype=$matchtype,	seqno=$seqno,	actionflags=$actionflags, vsys_name=$vsys_name,	device_name=$device_name,	vsys_id=$vsys_id,	srcipv6=$srcipv6,	hostid=$hostid  </p> </details> |
    | User-ID Log | <details> <summary><i> View Payload </i></summary> <p> timestamp=$time_generated, serial=$serial, type=$type, subtype=$subtype, vsys=$vsys,	network.client.ip=$ip,	usr.id=$user, datasourcename=$datasourcename,	evt.name=$eventid,	repeatcnt=$repeatcnt, timeout=$timeout,	network.client.port=$beginport,	network.destination.port=$endport,	datasource=$datasource,	datasourcetype=$datasourcetype,	seqno=$seqno,	actionflags=$actionflags, vsys_name=$vsys_name,	device_name=$device_name,	vsys_id=$vsys_id,	factortype=$factortype,	factorcompletiontime=$factorcompletiontime,,	factorno=$factorno,	ugflags=$ugflags,	userbysource=$userbysource  </p> </details> |
    | Tunnel Inspection Log | <details> <summary><i> View Payload </i></summary> <p> timestamp=$time_generated,	serial=$serial,	type=$type,	subtype=$subtype,	 network.client.ip=$src,	network.destination.ip=$dst,	natsrc=$natsrc,	natdst=$natdst,	rule=$rule,	usr.id=$srcuser,	dstuser=$dstuser,	app=$app,	vsys=$vsys,	from=$from,	to=$to,	inbound_if=$inbound_if,	outbound_if=$outbound_if,	logset=$logset,	sessionid=$sessionid,	repeatcnt=$repeatcnt,	network.client.port=$sport,	network.destination.port=$dport,	natsport=$natsport,	natdport=$natdport,	flags=$flags,	proto=$proto,	evt.outcome=$action,	severity=$severity,	seqno=$seqno,	actionflags=$actionflags,	srcloc=$srcloc,	dstloc=$dstloc,	vsys_name=$vsys_name,	device_name=$device_name,	tunnelid=$tunnelid,	monitortag=$monitortag,	parent_session_id=$parent_session_id,	parent_start_time=$parent_start_time,	tunnel=$tunnel,	bytes=$bytes,	network.bytes_read=$bytes_sent,	network.bytes_written=$bytes_received,	packets=$packets,	pkts_sent=$pkts_sent,	pkts_received=$pkts_received,	max_encap=$max_encap,	unknown_proto=$unknown_proto,	strict_check=$strict_check,	tunnel_fragment=$tunnel_fragment,	sessions_created=$sessions_created,	sessions_closed=$sessions_closed,	session_end_reason=$session_end_reason,	evt.name=$action_source,	start=$start,	elapsed=$elapsed,	tunnel_insp_rule=$tunnel_insp_rule  </p> </details> |
    | SCTP Log | <details> <summary><i> View Payload  </i></summary> <p> timestamp=$time_generated, serial=$serial, type=$type, network.client.ip=$src,	network.destination.ip=$dst, rule=$rule, vsys=$vsys, from=$from, to=$to, inbound_if=$inbound_if, outbound_if=$outbound_if, logset=$logset, sessionid=$sessionid,	repeatcnt=$repeatcnt,	network.client.port=$sport,	network.destination.port=$dport,	proto=$proto,	action=$action, vsys_name=$vsys_name,	device_name=$device_name,	seqno=$seqno,	assoc_id=$assoc_id,	ppid=$ppid,	severity=$severity,	sctp_chunk_type=$sctp_chunk_type,	sctp_event_type=$sctp_event_type,	verif_tag_1=$verif_tag_1,	verif_tag_2=$verif_tag_2,	sctp_cause_code=$sctp_cause_code,	diam_app_id=$diam_app_id,	diam_cmd_code=$diam_cmd_code,	diam_avp_code=$diam_avp_code,	stream_id=$stream_id,	assoc_end_reason=$assoc_end_reason,	op_code=$op_code,	sccp_calling_ssn=$sccp_calling_ssn,	sccp_calling_gt=$sccp_calling_gt,	sctp_filter=$sctp_filter,	chunks=$chunks,	chunks_sent=$chunks_sent,	chunks_received=$chunks_received,	packets=$packets,	pkts_sent=$pkts_sent,	pkts_received=$pkts_received  </p> </details> |
    | Config Log | <details> <summary><i> View Payload  </i></summary> <p> timestamp=$time_generated,	serial=$serial,	type=$type,	subtype=$subtype,	 network.client.ip=$host,	vsys=$vsys,	evt.name=$cmd,	usr.id=$admin,	client=$client,	evt.outcome=$result,	path=$path, before_change_detail=$before_change_detail,	after_change_detail=$after_change_detail,	seqno=$seqno,	actionflags=$actionflags, vsys_name=$vsys_name, device_name=$device_name  </p> </details> |
    | System Log | <details> <summary><i> View Payload </i></summary> <p> timestamp=$time_generated, serial=$serial, type=$type, subtype=$subtype,	vsys=$vsys,	evt.name=$eventid,	object=$object,	module=$module,	severity=$severity,	opaque=$opaque,	seqno=$seqno, actionflags=$actionflags, vsys_name=$vsys_name, device_name=$device_name  </p> </details> |
    | Correlated Events Log | <details> <summary><i> View Payload </i></summary> <p> timestamp=$time_generated, serial=$serial, type=$type, subtype=$subtype,	vsys=$vsys,	evt.name=$eventid,	object=$object,	module=$module,	severity=$severity,	opaque=$opaque,	seqno=$seqno, actionflags=$actionflags, vsys_name=$vsys_name,	device_name=$device_name  </p> </details> |
    | GTP Log  | <details> <summary><i> View Payload </i></summary> <p> timestamp=$start, serial=$serial, type=$type, subtype=$subtype,	network.client.ip=$src,	network.destination.ip=$dst, rule=$rule, app=$app, vsys=$vsys,	from=$from,	to=$to,	inbound_if=$inbound_if,	outbound_if=$outbound_if, logset=$logset,	sessionid=$sessionid,	network.client.port=$sport,	network.destination.port=$dport, proto=$proto,	evt.name=$action,	event_type=$event_type,	msisdn=$msisdn,	apn=$apn,	rat=$rat,	msg_type=$msg_type,	end_ip_adr=$end_ip_adr,	teid1=$teid1,	teid2=$teid2,	gtp_interface=$gtp_interface,	cause_code=$cause_code,	severity=$severity,	mcc=$mcc,	mnc=$mnc,	area_code=$area_code,	cell_id=$cell_id,	event_code=$event_code,	srcloc=$srcloc,	dstloc=$dstloc,	imsi=$imsi,	imei=$imei,	start=$start,	elapsed=$elapsed,	tunnel_insp_rule=$tunnel_insp_rule  </p> </details> |

 5. Click OK, this will create syslog server profile.
 6. Click on the Objects tab, this will open the log forwarding profile screen.
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

### Logs

The PANOS integration collects logs from the Palo Alto Networks firewall integration and forwards them to Datadog.

### Metrics

The PANOS integration does not include any metrics.

### Events

The PANOS integration does not send any events.

### Service Checks

The PANOS integration does not include any service checks.

## Further Reading

Additional helpful documentation, links, and articles:

- [Log types and fields][5]
- [Logs Collection documentation][6]

[1]: https://app.datadoghq.com/account/settings#agent
[2]: https://www.youtube.com/watch?v=LOPXg0oCMPs
[3]: https://docs.datadoghq.com/agent/guide/agent-configuration-files/?tab=agentv6v7
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[5]: https://docs.paloaltonetworks.com/pan-os/9-1/pan-os-admin/monitoring/use-syslog-for-monitoring/syslog-field-descriptions
[6]: https://docs.datadoghq.com/logs/log_collection/?tab=tailexistingfiles#getting-started-with-the-agent
