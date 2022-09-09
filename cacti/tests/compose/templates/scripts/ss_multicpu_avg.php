<?php
$no_http_headers = true;

/* display No errors */
error_reporting(E_ERROR);
include_once(dirname(__FILE__) . "/../include/config.php");
include_once(dirname(__FILE__) . "/../lib/snmp.php");
include_once(dirname(__FILE__) . "/../include/global.php");

if (!isset($called_by_script_server)) {
	array_shift($_SERVER["argv"]);
	print call_user_func_array("ss_multicpu_avg", $_SERVER["argv"]);
}




function ss_multicpu_avg ($hostname,$snmp_community,$snmp_auth_username, $snmp_auth_password, $snmp_auth_protocol, $snmp_priv_passphrase,$snmp_priv_protocol, $snmp_context, $snmp_version,$snmp_port, $snmp_timeout) {

    $snmp_retries   = read_config_option("snmp_retries");

    if ($snmp_version != 3) {
	$snmp_auth_username   	= "";
	$snmp_auth_password   	= "";
	$snmp_auth_protocol  	= "";
	$snmp_priv_passphrase 	= "";
	$snmp_priv_protocol   	= "";
	$snmp_context         	= "";

    }

	$oid_cpus = ".1.3.6.1.2.1.25.3.3.1.2";

//echo "cacti_snmp_walk($hostname, $snmp_community, $oid_cpus, $snmp_version, $snmp_auth_username, $snmp_auth_password, $snmp_auth_protocol, $snmp_priv_passphrase,  $snmp_priv_protocol, $snmp_context, $snmp_port, $snmp_timeout, 3, 64, SNMP_POLLER);";
	$array = cacti_snmp_walk($hostname, $snmp_community, $oid_cpus, $snmp_version, $snmp_auth_username, $snmp_auth_password, $snmp_auth_protocol, $snmp_priv_passphrase,  $snmp_priv_protocol, $snmp_context, $snmp_port, $snmp_timeout, $snmp_retries, 64, SNMP_POLLER);
	$load = 0;

	foreach ($array as $key=>$value)	{
	    $load += $value['value'];
	}

	$load = $load/count($array);


	return("load:$load\n");
}
?>