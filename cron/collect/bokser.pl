#!/usr/bin/perl

use SNMP_util;
use strict;

require '/usr/local/nav/navme/lib/NAV.pm';
import NAV qw(:DEFAULT :collect);;

my $localkilde = get_path("path_localkilde");
my $localconf = get_path("path_localconf");
my $lib = get_path("path_lib");

require $lib."snmplib.pl";

&log_open;

my $conn = &db_get("bokser");

my $mib_sysname = ".1.3.6.1.2.1.1.5.0";
my $mib_type =     ".1.3.6.1.2.1.1.2.0";

my (%sysnamehash,%server,%db_server,%nettel,%db_nettel,%alle,%db_alle);

#unntak: bokser p� watch
my %db_unntak = ();#&db_hent_enkel($conn,"select ip,watch from boks where watch='y' or watch='t'");

#sysname-endelser
#leses inn fra fil og legges i kolonseparert skalar
    my $fil_endelser = "$localconf/endelser.txt";
    my $endelser = &fil_endelser($fil_endelser);
    my %type = &db_hent_enkel($conn,"SELECT sysobjectid,typeid FROM type");
#-----------------------
#FILLESING: server.txt
my @felt_server = ("ip","sysname","roomid","orgid","catid","subcat","ro");
my $fil_server = "$localkilde/server.txt";
%server = &fil_server($fil_server,scalar(@felt_server),$endelser,\%sysnamehash);
#----------------------------------
#DATABASELESING

#hadde tenkt � ha med watch her, men vi bruker ikke snmp p� servere per dags dato. Kan bare settes p� n�r de ikke blir tatt med da de ikke svarer p� snmp.
%db_server = &db_hent_hash($conn,"SELECT ".join(",", @felt_server )." FROM netbox where catid = 'SRV'");
#legge til alle
for my $a (keys %db_server) {
    my $ip = $db_server{$a}[0];
    $db_alle{$ip} = 1;
}
#&device_endring($conn,\%server,\%db_server,\@felt_server,"netbox");
#&db_device($conn,"netbox",\@felt_server,[0],[0,1,2,3,4,5,6],\%server,\%db_server,0);
&db_safe(connection => $conn,table => "netbox",fields => \@felt_server, new => \%server, old => \%db_server,delete => 0,insert => "device");


#------------------------------
#FILLESING: nettel.txt
my @felt_nettel = ("ip","sysname","typeid","roomid","orgid","catid","subcat","ro","rw");
my $fil_nettel = "$localkilde/nettel.txt";
%nettel = &fil_nettel($fil_nettel,scalar(@felt_nettel),$endelser,\%db_unntak,\%sysnamehash);
#----------------------------------
#DATABASELESING
#felter som skal leses ut av databasen

%db_nettel = &db_hent_hash($conn,"SELECT ".join(",", @felt_nettel )." FROM netbox where catid <> 'SRV'");

#legge til i alle
for my $a (keys %db_nettel) {
    my $ip = $db_nettel{$a}[0];
    $db_alle{$ip} = 1;
}
&db_safe(connection => $conn,table => "netbox",fields => \@felt_nettel, new => \%nettel, old => \%db_nettel,delete => 0,insert => "device");

#-----------------------------------
#DELETE
    my @felt_alle = ("ip"); # felt som fungerer som sletteindex, i.e. ip
    &db_sletting($conn,\%alle,\%db_alle,\@felt_alle,"netbox");


&log_close;

# end main
#-----------------------------------------------------------------------

sub fil_endelser {
    my $fil = $_[0];
    open (FIL, "<$fil") || die ("kunne ikke �pne $fil");
    my @endelser;
    while (<FIL>) {
	next unless /^\./; 
	my $endelse = rydd($_);
	@endelser=(@endelser,$endelse);
    }
    close FIL;
    return join(":",@endelser);
}
sub fil_nettel{
    my ($fil,$felt,$endelser) = @_[0..2];
    my %unntak = %{$_[3]};
    my %sysnamehash = %{$_[4]};
    open (FIL, "<$fil") || die ("kunne ikke �pne $fil");
    while (<FIL>) {
	@_ = &fil_hent_linje($felt,$_);
	my $ip = $_[1];
	if($ip&&!exists($unntak{$ip})){
	    my $ro = $_[5];
	    if (my @passerr = $ro =~ /(\W)/g){ #sier fra hvis det finnes non-alfanumeriske tegn i passordet, og skriver ut (bare) disse tegnene.
		my $passerr = join "",@passerr;
		&skriv("TEXT-COMMUNITY", "ip=$ip","illegal=$passerr");
	    }
	    if (my @passerr = $_[6] =~ /(\W)/g){ #sier fra hvis det finnes non-alfanumeriske tegn i passordet, og skriver ut (bare) disse tegnene.
		my $passerr = join "",@passerr;
		&skriv("TEXT-COMMUNITY", "ip=$ip","illegal=$passerr");
	    }
	    my $temptype;
	    my $sysname;
# gammel    ($sysname,$temptype) = &snmp_system(1,$ip,$ro,$endelser);
	    ($sysname,$temptype) = &snmpsystem($ip,$ro,$endelser);
	    ($sysname,%sysnamehash) = &sysnameuniqueify($sysname,\%sysnamehash);
	    my $type = $type{$temptype};
	    if($sysname){
		unless($type){
		    &skriv("TEXT-TYPE","ip=$ip","type=$temptype");
		}
		@_ = ($ip,$sysname,$type,$_[0],$_[2],@_[3..6]);
		@_ = map rydd($_), @_;

		unless (exists($alle{$ip})){
		    $nettel{$ip} = [ @_ ];
		}
	    }
	    # m� legges inn s� lenge den eksisterer i fila, uavhengig av snmp
	    unless (exists($alle{$ip})){
		$alle{$ip} = 1;
	    } else {
		&skriv("IP-ALREADY","ip=$ip","last=".$nettel{$ip}[1]);
	    }
#	    print $sysname.$type."\n";
	}
	
    }
    close FIL;
    return %nettel;
}
sub fil_server{
    my ($fil,$felt,$endelser) = @_;
    my %sysnamehash = %{$_[3]};
    open (FIL, "<$fil") || die ("kunne ikke �pne $fil");
    while (<FIL>) {

	@_ = &fil_hent_linje($felt,$_);
	my $ip;
	if($ip = &hent_ip($_[1])) {
	    @_ = ($ip,@_[0..1],lc($_[2]),uc($_[3]),@_[4..5]);
	    @_ = map rydd($_), @_;
	    my $sysname = &fjern_endelse($_[2],$endelser);
	    ($sysname,%sysnamehash) = &sysnameuniqueify($sysname,\%sysnamehash);
	    unless (exists($alle{$ip})){
		$server{$ip} = [ $ip,$sysname,$_[1],@_[3..6] ];
	    }
	    unless (exists($alle{$ip})){
		$alle{$ip} = 1;
	    } else {
		&skriv("IP-ALREADY","ip=$ip","last=".$server{$ip}[1]);
	    }
	}
    }
    close FIL;
    return %server;
}

sub sysnameuniqueify {
    my $sysnameroot = $_[0];
    my %sysnamehash = %{$_[1]};
    
    my $ok = 0; #intern
    my $v = 1;
    my $sysname = $sysnameroot;

    until($ok){

	unless(exists($sysnamehash{$sysname})){
	    $sysnamehash{$sysname} = 1;
	    $ok = 1;
	} else {
	    $v++;
	    $sysname = $sysnameroot.",v".$v;
	}
    }
    &skriv("DEVICE-COLLECT","ip=$sysname");
    return ($sysname,\%sysnamehash);

}

