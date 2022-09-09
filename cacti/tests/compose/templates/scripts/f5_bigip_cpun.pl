#!/usr/bin/perl -w
# This code is not supported by F5 Network and is offered under the GNU General Public License.  Use at your own risk.

#use strict;
use Net::SNMP qw(:snmp);

my ($host, $snmp_comm);

$host = $ARGV[0];
$snmp_comm = $ARGV[1];
chomp ($host , $snmp_comm);

#my $cpuID        = ".1.3.6.1.4.1.3375.2.1.7.5.2.1.3.1.48";
my $cpuIndex     = ".1.3.6.1.4.1.3375.2.1.7.5.2.1.2.1.48";

my $cpuUsageRatio5s = ".1.3.6.1.4.1.3375.2.1.7.5.2.1.19.1.48.";
my $cpuUsageRatio1m = ".1.3.6.1.4.1.3375.2.1.7.5.2.1.27.1.48.";
my $cpuUsageRatio5m = ".1.3.6.1.4.1.3375.2.1.7.5.2.1.35.1.48.";

my $gcpuUsageRatio5s = ".1.3.6.1.4.1.3375.2.1.1.2.20.21.0";
my $gcpuUsageRatio1m = ".1.3.6.1.4.1.3375.2.1.1.2.20.29.0";
my $gcpuUsageRatio5m = ".1.3.6.1.4.1.3375.2.1.1.2.20.37.0";

my ($session, $error) = Net::SNMP->session(
            -hostname       => $host,
            -community      => $snmp_comm,
            -port           => 161,
            -version        => 'snmpv2c',
            -nonblocking    => 0
            );

if (!defined $session) {
        print "Received no SNMP response from $host\n";
        print STDERR "Error: $error\n";
        exit -1;
        }
    
my $allCPU = $session->get_table ( -baseoid => $cpuIndex );
my %cpu_table = %{$allCPU};
my $x = 0;

foreach my $key (sort keys %cpu_table) {
	@oid_index = split(/\./, $key);
	my $ltm_cpu5s = $cpuUsageRatio5s . $oid_index[-1];
	my $ltm_cpu1m = $cpuUsageRatio1m . $oid_index[-1];
	my $ltm_cpu5m = $cpuUsageRatio5m . $oid_index[-1];

	my $oid_ratios = $session->get_request(
		-varbindlist =>
		[$ltm_cpu5s, $ltm_cpu1m, $ltm_cpu5m] );

	print "CPU$x\_5s:$oid_ratios->{$ltm_cpu5s} CPU$x\_1m:$oid_ratios->{$ltm_cpu1m} CPU$x\_5m:$oid_ratios->{$ltm_cpu5m} ";
	$x++;
}

my $oid_gratios = $session->get_request(
	-varbindlist =>
	[$gcpuUsageRatio5s, $gcpuUsageRatio1m, $gcpuUsageRatio5m] );

print " Global_5s:$oid_gratios->{$gcpuUsageRatio5s} Global_1m:$oid_gratios->{$gcpuUsageRatio1m} Global_5m:$oid_gratios->{$gcpuUsageRatio5m}";
