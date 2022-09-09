<?php


/* do NOT run this script through a web browser */
if (!isset($_SERVER["argv"][0]) || isset($_SERVER['REQUEST_METHOD'])  || isset($_SERVER['REMOTE_ADDR'])) {
   die("<br><strong>This script is only meant to run at the command line.</strong>");
}

$no_http_headers = true;

include(dirname(__FILE__)."/../include/global.php");
include(dirname(__FILE__)."/../lib/snmp.php");

$oids = array(
        "index"			=> ".1.3.6.1.4.1.2636.5.1.1.2.1.1.1.14",
        "peerip"		=> ".1.3.6.1.4.1.2636.5.1.1.2.1.1.1.14",
        "received"		=> ".1.3.6.1.4.1.2636.5.1.1.2.6.2.1.7",
        "accepted"		=> ".1.3.6.1.4.1.2636.5.1.1.2.6.2.1.8",
        "rejected"		=> ".1.3.6.1.4.1.2636.5.1.1.2.6.2.1.9",
        "sent"			=> ".1.3.6.1.4.1.2636.5.1.1.2.6.2.1.10",
        );
$xml_delimiter                  =  "!";

$hostname       = $_SERVER["argv"][1];
$snmp_auth      = $_SERVER["argv"][2];
$cmd            = $_SERVER["argv"][3];

/* support for SNMP V2 and SNMP V3 parameters */
$snmp = explode(":", $snmp_auth);
$snmp_version   = $snmp[0];
$snmp_port      = $snmp[1];
$snmp_timeout   = $snmp[2];
$ping_retries   = $snmp[3];
$max_oids       = $snmp[4];

$snmp_auth_username     = "";
$snmp_auth_password     = "";
$snmp_auth_protocol     = "";
$snmp_priv_passphrase   = "";
$snmp_priv_protocol     = "";
$snmp_context           = "";
$snmp_community         = "";

if ($snmp_version == 3) {
        $snmp_auth_username   = $snmp[6];
        $snmp_auth_password   = $snmp[7];
        $snmp_auth_protocol   = $snmp[8];
        $snmp_priv_passphrase = $snmp[9];
        $snmp_priv_protocol   = $snmp[10];
        $snmp_context         = $snmp[11];
}else{
        $snmp_community = $snmp[5];
}


/* process index requests */
if ($cmd == "index") {
        $return_arr = cacti_snmp_walk($hostname, $snmp_community, $oids['index'], $snmp_version, $snmp_auth_username, $snmp_auth_password, $snmp_auth_protocol, $snmp_priv_passphrase, $snmp_priv_protocol, $snmp_context, $snmp_port, $snmp_timeout, $ping_retries, $max_oids, SNMP_POLLER);

        foreach ($return_arr as $arr) {
                print $arr["value"] . "\n";
        }

/* process query requests */
} elseif ($cmd == "query") {
        $arg = $_SERVER["argv"][4];

        if ($arg == "peerip") {
                $return_arr = cacti_snmp_walk($hostname, $snmp_community, $oids[$arg], $snmp_version, $snmp_auth_username, $snmp_auth_password, $snmp_auth_protocol, $snmp_priv_passphrase, $snmp_priv_protocol, $snmp_context, $snmp_port, $snmp_timeout, $ping_retries, $max_oids, SNMP_POLLER);
                foreach ($return_arr as $arr) {
                        $temp = explode(".", $arr["oid"]);
                        $peer["ip"] = $temp[22] . "." . $temp[23] . "." . $temp[24] . "." . $temp[25];
                        print $arr["value"] . "!" . $peer["ip"] . "\n";
                }
        } elseif ($arg == "received") {
                $return_arr = cacti_snmp_walk($hostname, $snmp_community, $oids['index'], $snmp_version, $snmp_auth_username, $snmp_auth_password, $snmp_auth_protocol, $snmp_priv_passphrase, $snmp_priv_protocol, $snmp_context, $snmp_port, $snmp_timeout, $ping_retries, $max_oids, SNMP_POLLER);
                foreach ($return_arr as $arr) {

                        $return_arr2 = cacti_snmp_walk($hostname, $snmp_community, $oids[$arg] . "." . $arr["value"], $snmp_version, $snmp_auth_username, $snmp_auth_password, $snmp_auth_protocol, $snmp_priv_passphrase, $snmp_priv_protocol, $snmp_context, $snmp_port, $snmp_timeout, $ping_retries, $max_oids, SNMP_POLLER);
                        foreach ($return_arr2 as $arr2) {
                                if ($arr2["value"]) {
                                        print $arr["value"] . "!" . $arr2["value"] . "\n";
                                }
                        }
                }
        } elseif ($arg == "accepted") {
                $return_arr = cacti_snmp_walk($hostname, $snmp_community, $oids['index'], $snmp_version, $snmp_auth_username, $snmp_auth_password, $snmp_auth_protocol, $snmp_priv_passphrase, $snmp_priv_protocol, $snmp_context, $snmp_port, $snmp_timeout, $ping_retries, $max_oids, SNMP_POLLER);
                foreach ($return_arr as $arr) {

                        $return_arr3 = cacti_snmp_walk($hostname, $snmp_community, $oids[$arg] . "." . $arr["value"], $snmp_version, $snmp_auth_username, $snmp_auth_password, $snmp_auth_protocol, $snmp_priv_passphrase, $snmp_priv_protocol, $snmp_context, $snmp_port, $snmp_timeout, $ping_retries, $max_oids, SNMP_POLLER);
                        foreach ($return_arr3 as $arr3) {
                                if ($arr3["value"]) {
                                        print $arr["value"] . "!" . $arr3["value"] . "\n";
                                }
                        }
                }
        } elseif ($arg == "rejected") {
                $return_arr = cacti_snmp_walk($hostname, $snmp_community, $oids['index'], $snmp_version, $snmp_auth_username, $snmp_auth_password, $snmp_auth_protocol, $snmp_priv_passphrase, $snmp_priv_protocol, $snmp_context, $snmp_port, $snmp_timeout, $ping_retries, $max_oids, SNMP_POLLER);
                foreach ($return_arr as $arr) {

                        $return_arr4 = cacti_snmp_walk($hostname, $snmp_community, $oids[$arg] . "." . $arr["value"], $snmp_version, $snmp_auth_username, $snmp_auth_password, $snmp_auth_protocol, $snmp_priv_passphrase, $snmp_priv_protocol, $snmp_context, $snmp_port, $snmp_timeout, $ping_retries, $max_oids, SNMP_POLLER);
                        foreach ($return_arr4 as $arr4) {
                                if ($arr4["value"]) {
                                        print $arr["value"] . "!" . $arr4["value"] . "\n";
                                }
                        }
                }
        } elseif ($arg == "sent") {
                $return_arr = cacti_snmp_walk($hostname, $snmp_community, $oids['index'], $snmp_version, $snmp_auth_username, $snmp_auth_password, $snmp_auth_protocol, $snmp_priv_passphrase, $snmp_priv_protocol, $snmp_context, $snmp_port, $snmp_timeout, $ping_retries, $max_oids, SNMP_POLLER);
                foreach ($return_arr as $arr) {

                        $return_arr5 = cacti_snmp_walk($hostname, $snmp_community, $oids[$arg] . "." . $arr["value"], $snmp_version, $snmp_auth_username, $snmp_auth_password, $snmp_auth_protocol, $snmp_priv_passphrase, $snmp_priv_protocol, $snmp_context, $snmp_port, $snmp_timeout, $ping_retries, $max_oids, SNMP_POLLER);
                        foreach ($return_arr5 as $arr5) {
                                if ($arr5["value"]) {
                                        print $arr["value"] . "!" . $arr5["value"] . "\n";
                                }
                        }
                }
        } elseif ($arg == "index") {
                $return_arr = cacti_snmp_walk($hostname, $snmp_community, $oids['index'], $snmp_version, $snmp_auth_username, $snmp_auth_password, $snmp_auth_protocol, $snmp_priv_passphrase, $snmp_priv_protocol, $snmp_context, $snmp_port, $snmp_timeout, $ping_retries, $max_oids, SNMP_POLLER);

                foreach ($return_arr as $arr) {
                        print $arr["value"] . "!" . $arr["value"] . "\n";
                }
        }

/* process prefix requests */
} elseif ($cmd == "get") {
        $arg = $_SERVER["argv"][4];
        $index = $_SERVER["argv"][5];

        if ($arg == "received") {
                $return_arr2 = cacti_snmp_walk($hostname, $snmp_community, $oids[$arg] . ".$index", $snmp_version, $snmp_auth_username, $snmp_auth_password, $snmp_auth_protocol, $snmp_priv_passphrase, $snmp_priv_protocol, $snmp_context, $snmp_port, $snmp_timeout, $ping_retries, $max_oids, SNMP_POLLER);
                foreach ($return_arr2 as $arr) {
                        if ($arr["value"] >= 0) {
                                print $arr["value"];
                        }
                }
        }
        elseif ($arg == "accepted") {
                $return_arr3 = cacti_snmp_walk($hostname, $snmp_community, $oids[$arg] . ".$index", $snmp_version, $snmp_auth_username, $snmp_auth_password, $snmp_auth_protocol, $snmp_priv_passphrase, $snmp_priv_protocol, $snmp_context, $snmp_port, $snmp_timeout, $ping_retries, $max_oids, SNMP_POLLER);
                foreach ($return_arr3 as $arr) {
                        if ($arr["value"] >= 0) {
                                print $arr["value"];
                        }
                }
        }
        elseif ($arg == "rejected") {
                $return_arr4 = cacti_snmp_walk($hostname, $snmp_community, $oids[$arg] . ".$index", $snmp_version, $snmp_auth_username, $snmp_auth_password, $snmp_auth_protocol, $snmp_priv_passphrase, $snmp_priv_protocol, $snmp_context, $snmp_port, $snmp_timeout, $ping_retries, $max_oids, SNMP_POLLER);
                foreach ($return_arr4 as $arr) {
                        if ($arr["value"] >= 0) {
                                print $arr["value"];
                        }
                }
        }
        elseif ($arg == "sent") {
                $return_arr5 = cacti_snmp_walk($hostname, $snmp_community, $oids[$arg] . ".$index", $snmp_version, $snmp_auth_username, $snmp_auth_password, $snmp_auth_protocol, $snmp_priv_passphrase, $snmp_priv_protocol, $snmp_context, $snmp_port, $snmp_timeout, $ping_retries, $max_oids, SNMP_POLLER);
                foreach ($return_arr5 as $arr) {
                        if ($arr["value"] >= 0) {
                                print $arr["value"];
                        }
                }
        }
}
?>