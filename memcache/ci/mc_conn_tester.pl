#! /usr/bin/perl
# Written by Dormando, Eric Bergen, and HaiXin Tie.
# PUBLIC DOMAIN.
# No guarantees it won't eat your cat.

use warnings;
use strict;

use IO::Socket::INET;
use Time::HiRes qw/time sleep/;
use Getopt::Long qw(:config no_ignore_case);
use List::Util qw(first max maxstr min minstr reduce shuffle sum);
use Pod::Usage;

use FindBin;

my $server = '127.0.0.1';
my $port = '11211';
my $time = 0;
my $timeout = 1;
my $count = 0;
my $emt = 0;
my $help;
my $script_start_time = time();

my $debug = 1;

my $average_conn = 0;
my $average_set  = 0;
my $average_get  = 0;
my $actual_count = 0;

my $max_conn = 0;
my $max_set = 0;
my $max_get = 0;

sub parse_params {
    my $sendHelp;

    if (! &Getopt::Long::GetOptions(
        'server|s=s'          => \$server,
        'port|p=s'            => \$port,
        'time|t=s'            => \$time,
        'timeout|o=s'         => \$timeout,
        'count|c=s'           => \$count,
        'emt|e'             => \$emt,
        'help|h'            => \$help
        ))
    {
        pod2usage(0);
        exit(1);
    }

    if ($count && $time) {
        print "Either count or time should be specified, not both.";
        $help = 1;
    }

    if (!$count && !$time) {
        # Make the default behavior closer to the old script
        $count = 100_000_000;
    }

    if ($help) {
        pod2usage(1);
        exit(1);
    }
}

sub keep_running
{
    my ($run) = @_;

    if ($time && time() - $script_start_time > $time)
    {
        return 0;
    } elsif ($count && $run == $count) {
        return 0;
    }

    return 1;
}

sub human_output
{
    printf "Average: (conn: %.8f) (set: %0.8f) (get: %.8f)\n",
        $average_conn, $average_set, $average_get;
    printf "Max: (conn: %.8f) (set: %0.8f) (get: %.8f)\n",
        $max_conn, $max_set, $max_get;
    print "Done\n";
}

sub emt_output
{
    $average_conn *= 1000;
    $average_set *= 1000;
    $average_get *= 1000;
    $max_conn *= 1000;
    $max_set *= 1000;
    $max_get *= 1000;

    # echo memcached_test_{average,max}_{get,set,con}
    printf "memcached_test_average_con=%.5f," .
           "memcached_test_average_set=%.5f," .
           "memcached_test_average_get=%.5f," .
           "memcached_test_max_con=%.5f," .
           "memcached_test_max_set=%.5f," .
           "memcached_test_max_get=%.5f\n",
           $average_conn, $average_set, $average_get,
           $max_conn, $max_set, $max_get;
}


parse_params();


$SIG{INT} = sub {
    printf "Averages: (conn: %.8f) (set: %0.8f) (get: %.8f)\n",
        $average_conn, $average_set, $average_get;
    exit;
};

$|++;
my $run = 0;
while (keep_running($run)) {
    $run++;
    my $conn_time = 0;
    my $set_time  = 0;
    my $get_time  = 0;
    my $start     = 0;
    eval {
        local $SIG{ALRM} = sub { die "alarm\n" };
        alarm $timeout;
        $start = time();
        my $sock = IO::Socket::INET->new(PeerAddr => "$server:$port",
                                     Timeout  => $timeout + 1);
        die "$!\n" unless $sock;
        $conn_time = time();

        my $len = length($run);
        for (1 .. 3) {
            print $sock "set foo 0 0 $len\r\n$run\r\n";
            my $res = <$sock>;
        }
        $set_time = time();
        for (1 .. 6) {
            print $sock "get foo\r\n";
            my $val = <$sock>;
        }
        $get_time = time();
    };
    alarm 0;
    my $end_time = time();

    # Note for this round.
    my $conn_elapsed = $conn_time ? ($conn_time - $start) : 0;
    my $set_elapsed  = $set_time ? ($set_time - $conn_time) : 0;
    my $get_elapsed  = $get_time ? ($get_time - $set_time) : 0;
    my $elapsed      = $end_time - $start;
    if ($@) {
        if ($@ eq "alarm\n") {
            printf "Fail: (timeout: $timeout) (elapsed: %.8f) (conn: %.8f)"
                . " (set: %0.8f) (get: %.8f)\n", $elapsed, $conn_elapsed,
                $set_elapsed, $get_elapsed;
        } else {
            print "Failed for some other reason: $@ - looping\n";
        }
    } elsif ($debug) {
       printf "loop: (timeout: $timeout) (elapsed: %.8f) (conn: %.8f)"
       . " (set: %0.8f) (get: %.8f)\n", $elapsed, $conn_elapsed,
       $set_elapsed, $get_elapsed;
    }

    # Sum up the averages.
    if ($conn_elapsed) {
        $average_conn += $conn_elapsed;

        if ($conn_elapsed > $max_conn) {
            $max_conn = $conn_elapsed;
        }
    }

    if ($set_elapsed) {
        $average_set += $set_elapsed;

        if ($set_elapsed > $max_set) {
            $max_set = $set_elapsed;
        }
    }

    if ($get_elapsed) {
        $average_get += $get_elapsed;

        if ($get_elapsed > $max_get) {
            $max_get = $get_elapsed;
        }

    }
    $actual_count++;

    # Sleep a short time inbetween.
    sleep 0.1;
}

# average calculation.
if ($average_conn && $actual_count) {
    $average_conn /= $actual_count;
}

if ($average_set && $actual_count) {
    $average_set /= $actual_count;
}

if ($average_get && $actual_count) {
    $average_get /= $actual_count;
}

if ($emt) {
    emt_output();
} else {
    human_output();
}

__END__

=head1  mc_conn_tester_pl - Report average and max get, set, and connection time to memcached.

=head1 SYNOPSIS

mc_conn_tester.pl [options]

=head1 OPTIONS

=over 8

=item B<-s --server> hostname

Connect to an alternate hostname.

=item B<-p --port> port

Connect to an alternate port.

=item B<-t --time> time

Collect statistics for time seconds. Only specify --time or --count.

=item B<-c --count> count

Collect statistics for count iterations. Only specify --count or --time.

=item B<-o --timeout> seconds

Amounht of time in seconds to consider the request timed out (default 1)

=item B<-e --emt>

Ouptut the restuls in a a csv format that can be used by EMT to log results.

=item B<-h --help>

This help.

=cut
