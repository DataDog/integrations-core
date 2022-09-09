#!/usr/bin/perl 
# Originally contributed by James Kelty
# Modified for v.10 by Jason Rahm
# 

use Net::SNMP qw(:snmp); 

my $host = $ARGV[0]; 
my $snmp_comm = $ARGV[1]; 

($time,$idle,$sleep) = &getValue($host,$snmp_comm); 
sleep(10); 
($time1,$idle1,$sleep1) = &getValue($host,$snmp_comm); 

$time_delta = $time1 - $time; 
$idle_delta = $idle1 - $idle; 
$sleep_delta = $sleep1 - $sleep; 

$tmm_usage = &calcCPU($time_delta, $idle_delta, $sleep_delta);

print "$tmm_usage"; 

sub getValue { 

    use Net::SNMP qw(:snmp); 

    my ($host,$snmp_comm) = (@_); 
    my $tmmTotalCycles = '.1.3.6.1.4.1.3375.2.1.1.2.1.41.0'; 
    my $tmmIdleCycles  = '.1.3.6.1.4.1.3375.2.1.1.2.1.42.0'; 
    my $tmmSleepCycles = '.1.3.6.1.4.1.3375.2.1.1.2.1.43.0'; 

    my ($session,$error) = Net::SNMP->session( 
 	-hostname 	=> $host, 
 	-community	=> $snmp_comm, 
 	-port		=> 161, 
 	-version	=> 'snmpv2c', 
 	-nonblocking	=> 0 
 	); 

    if (!defined $session)  { 
 	print "Recieved no SNMP response from $host\n"; 
 	print STDERR "Error: $error\n"; 
 	exit -1; 
 	} 

    my $polled_oids = $session->get_request( 
 		-varbindlist 	=> [$tmmTotalCycles,$tmmIdleCycles,$tmmSleepCycles] 
 		); 

    my $total_time = $polled_oids->{$tmmTotalCycles}; 
    my $total_idle = $polled_oids->{$tmmIdleCycles}; 
    my $total_sleep = $polled_oids->{$tmmSleepCycles}; 

    return($total_time,$total_idle,$total_sleep); 
} 

sub calcCPU {
	my ($timeDelta, $idleDelta, $sleepDelta) = @_;
	my $cpu_percentage =  int((($timeDelta - ($idleDelta + $sleepDelta)) / $timeDelta )*100 +.5);
	return($cpu_percentage);
}
