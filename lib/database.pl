#!/usr/bin/perl -w
#
# $Id: database.pl,v 1.11 2002/07/23 10:04:53 mortenv Exp $
#

use Pg;
use strict;
require "/usr/local/nav/navme/lib/fil.pl";

my $debug=1;
my $navdir = "/usr/local/nav/";

sub db_hent {
    my ($db,$sql) = @_;
    return &db_select($db,$sql);
}
sub db_hent_hash {
    my ($db,$sql) = @_;
    my $res = &db_select($db,$sql);
    my %resultat;
    while(@_ = $res->fetchrow) {
	@_ = map rydd($_), @_;
	$resultat{$_[0]} = [ @_ ];
    }
    return %resultat;
}
sub db_hent_array {
    my ($db,$sql) = @_;
    my $res = &db_select($db,$sql);
    my @resultat;
    my $i;
    while(@_ = $res->fetchrow) {
	@_ = map rydd($_), @_;
	$resultat[$i] = [ @_ ];
	$i++;
    }
    return @resultat;
}
sub db_hent_hash_konkatiner {
    my ($db,$sql) = @_;
    my $res = &db_select($db,$sql);
    my %resultat;
    while(@_ = $res->fetchrow) {
	@_ = map rydd($_), @_;
	$resultat{"$_[1]\/$_[2]"} = [ @_ ];
    }
    return %resultat;
}

sub db_hent_enkel {
## Henter ut hash indeksert p� f�rste ledd i sql-setning. 
## N�kkelen er f�rste ledd
## Verdien er andre ledd
    my ($db,$sql) = @_;
    my %resultat = ();
    my $res =  &db_select($db,$sql);
    while(@_ = $res->fetchrow) {
	@_ = map rydd($_), @_;
	$resultat{$_[0]} = $_[1] ;
    }
    return %resultat;
}
sub db_hent_dobbel {
    my ($db,$sql) = @_;
    my %resultat = ();
    my $res =  &db_select($db,$sql);
    while(@_ = $res->fetchrow) {
	@_ = map rydd($_), @_;
	$resultat{$_[0]}{$_[1]} = $_[2] ;
    }
    return %resultat;
}

sub db_select_hash {
    my $db = $_[0];
    my $tabell = $_[1];
    my @felt = @{$_[2]};
    my $en = $_[3];
    my $to = $_[4];
    my $tre = $_[5];

    my %resultat;
    my $sql = "SELECT ".join(",", @felt)." FROM $tabell";
    my $res =  &db_select($db,$sql);

    if(defined($tre)){
	while(@_ = $res->fetchrow) {
	    @_ = map rydd($_), @_;
	    $resultat{$_[$en]}{$_[$to]}{$_[$tre]} = [ @_ ] ;
	}
    } elsif (defined($to)) {
	while(@_ = $res->fetchrow) {
	    @_ = map rydd($_), @_;
	    $resultat{$_[$en]}{$_[$to]} = [ @_ ] ;
	}
    } elsif (defined($en)){
	while(@_ = $res->fetchrow) {
	    @_ = map rydd($_), @_;
	    $resultat{$_[$en]} = [ @_ ] ;
	}
    }
    return %resultat;
}

sub db_sql_hash {
    my $db = $_[0];
    my $sql = $_[1];
#    my @felt = @{$_[2]};
    my $en = $_[2];
    my $to = $_[3];
    my $tre = $_[4];
    print $sql;
    my $felt = $sql =~ /SELECT(.*)FROM/is;
    print $felt;
    my @felt = split /\, */,$felt;

    my %resultat;
    print $sql = "SELECT ".join(",", @felt)." FROM ";
    my $res =  &db_select($db,$sql);

    if(defined($tre)){
	while(@_ = $res->fetchrow) {
	    @_ = map rydd($_), @_;
	    $resultat{$_[$en]}{$_[$to]}{$_[$tre]} = [ @_ ] ;
	}
    } elsif (defined($to)) {
	while(@_ = $res->fetchrow) {
	    @_ = map rydd($_), @_;
	    $resultat{$_[$en]}{$_[$to]} = [ @_ ] ;
	}
    } elsif (defined($en)){
	while(@_ = $res->fetchrow) {
	    @_ = map rydd($_), @_;
	    $resultat{$_[$en]} = [ @_ ] ;
	}
    }
    return %resultat;
}




sub db_hent_dobbel_hash_konkatiner {
    my ($db,$sql) = @_;
    my %resultat = ();
    my $res =  &db_select($db,$sql);
    while(@_ = $res->fetchrow) {
	@_ = map rydd($_), @_;
	$resultat{$_[1]}{$_[2]."/".$_[3]} = @_ ;
    }
    return %resultat;
}
sub db_hent_scalar {
    my ($db,$sql) = @_;
    my $resultat;
    my $res =  &db_select($db,$sql);
    while(@_ = $res->fetchrow) {
	@_ = map rydd($_), @_;
	$resultat = $_[1] ;
    }
    return $resultat;
}
sub db_sett_inn {
    my ($db,$tabell,$felt,$verdier) = @_;
    my @felt = split/:/,$felt;
    my @verdier = split/:/,$verdier;
    my @val;
    my @key;
    foreach my $i (0..$#felt) {
	if (defined($verdier[$i]) && $verdier[$i] ne ''){
	    #normal
	    push(@val, "\'".$verdier[$i]."\'");
	    push(@key, $felt[$i]);
#	} elsif (defined($verdier[$i])) {
	    #null
#	    push(@val, "NULL");
#	    push(@key, $felt[$i]);
	}
    }
    if(scalar(@key)){ #key eksisterer
	my $sql = "INSERT INTO $tabell (".join(",",@key ).") VALUES (".join(",",@val).")";
	print $sql if $debug;
	&skriv("DATABASE-INSERT","tuple=".join(" ",@val),"table=$tabell") if &db_execute($db,$sql);

    }
}
sub db_insert {
    my $db = $_[0];
    my $tabell = $_[1];
    my @felt = @{$_[2]};
    my @verdier = @{$_[3]};

    my @val;
    my @key;
    foreach my $i (0..$#felt) {
#	print $verdier[$i]."\n";
	if (defined($verdier[$i]) && $verdier[$i] ne ''){
	    push(@val, "\'".$verdier[$i]."\'");
	    push(@key, $felt[$i]);
	}
    }
    if(scalar(@key)){
	my $sql = "INSERT INTO $tabell (".join(",",@key ).") VALUES (".join(",",@val).")";
	&db_execute($db,$sql);
    }
}
sub db_logg_insert {
    my $db = $_[0];
    my $tabell = $_[1];
    my @felt = @{$_[2]};
    my @verdier = @{$_[3]};

    my @val;
    my @key;
    foreach my $i (0..$#felt) {
#	print $verdier[$i]."\n";
	if (defined($verdier[$i]) && $verdier[$i] ne ''){
	    #normal
	    push(@val, "\'".$verdier[$i]."\'");
	    push(@key, $felt[$i]);
#	} elsif (defined($verdier[$i])) {
	    #null
#	    push(@val, "NULL");
#	    push(@key, $felt[$i]);
	}
    }
    if(scalar(@key)){ #key eksisterer
#	my $nql = "\n\nSETTER INN I |$tabell| FELT |".join(" ",@key)."| VERDIER |".join(" ",@val)."|";
	my $sql = "INSERT INTO $tabell (".join(",",@key ).") VALUES (".join(",",@val).")";
	&skriv("DATABASE-INSERT", "table=$tabell", "tuple=".join(" ",@val)) if &db_execute($db,$sql);
    }
}
sub db_update {
    my ($db,$tabell,$felt,$fra,$til,$hvor) = @_;
    if(defined( $fra ) && defined( $til )){
    unless($til eq $fra) {
#	print "***IKKE LIKE\n";
	if (!$til && $fra){
	    my $sql = "UPDATE $tabell SET $felt=null WHERE $hvor";
#	    my $nql = "\n\nOPPDATERER |$tabell| FELT |$felt| FRA |$fra| TIL |null| hvor |$hvor|";
	    &skriv("DATABASE-UPDATE", "from=$fra","to=null","where=$hvor","table=$tabell", "field=$felt") if &db_execute($db,$sql);

	} elsif ($til) {
	    my $sql = "UPDATE $tabell SET $felt=\'$til\' WHERE $hvor";
#	    my $nql = "\n\nOPPDATERER |$tabell| FELT |$felt| FRA |$fra| TIL |$til| hvor |$hvor|";
	    &skriv("DATABASE-UPDATE", "from=$fra","to=$til","where=$hvor","table=$tabell","field=$felt") if &db_execute($db,$sql);
	    print $sql if $debug;
#	} else {
#	    print "tomme: $til & $fra\n";
	}
    }
    }
}

sub db_oppdater {
    my ($db,$tabell,$felt,$fra,$til,$hvor_nokkel,$hvor_passer) = @_;

    my $sql = "UPDATE $tabell SET $felt=$til WHERE $hvor_nokkel=\'$hvor_passer\'";
    &skriv("DATABASE-UPDATE", "from=$fra","to=$til","where=$hvor_nokkel = $hvor_passer","table=$tabell","field=$felt") if &db_execute($db,$sql);

    print $sql if $debug;
}
#ikke i bruk
sub db_oppdater_idant_to {
    my ($db,$tabell,$felt,$fra,$til,$hvor_nokkel1,$hvor_nokkel2,$hvor_passer1,$hvor_passer2) = @_;

    &skriv("DBOUT", "\n\nOppdaterer *$tabell* felt *$felt* fra *$fra* til *$til* hvor *$hvor_nokkel1* er *$hvor_passer1* og *$hvor_nokkel2* er *$hvor_passer2*");
    my $sql = "UPDATE $tabell SET $felt=$til WHERE $hvor_nokkel1=\'$hvor_passer1\' AND $hvor_nokkel2=\'$hvor_passer2\'";
    &db_execute($db,$sql);
#    print $sql,"\n";
}

sub db_delete {
    my ($db,$tabell,$hvor) = @_;
#    my $nql = "\n\nSLETTER FRA TABELL |$tabell| HVOR |$hvor|";
    my $sql = "DELETE FROM $tabell WHERE $hvor";
    &skriv("DATABASE-DELETE", "table=$tabell","where=$hvor");
  &db_execute($db,$sql);

#    print $sql;
}    
sub db_slett {
    my ($db,$tabell,$hvor_nokkel,$hvor_passer) = @_;
    if($hvor_passer){
	my $sql = "DELETE FROM $tabell WHERE $hvor_nokkel=\'$hvor_passer\'";
	&skriv("DATABASE-DELETE", "table=$tabell","where=$hvor_nokkel = $hvor_passer");
	&db_execute($db,$sql);

	print $sql if $debug;
    }
}    
#ikke i bruk
sub db_slett_idant_to {
    my ($db,$tabell,$hvor_nokkel1,$hvor_nokkel2,$hvor_passer1,$hvor_passer2) = @_;


    &skriv("DBOUT", "\n\nSletter fra *$tabell* hvor $hvor_nokkel1 = $hvor_passer1");
    my $sql = "DELETE FROM $tabell WHERE $hvor_nokkel1=\'$hvor_passer1\' AND $hvor_nokkel2=\'$hvor_passer2\'";
   &db_execute($db,$sql);
    print $sql if $debug;
}    

sub db_sletting{
    my $db = $_[0];
    my %ny = %{$_[1]};
    my %gammel = %{$_[2]};
    my @felt = @{$_[3]};
    my $tabell = $_[4];
#-----------------------------------
#DELETE
    #hvis den ikke ligger i fila
    for my $f (keys %gammel) {
	unless(exists($ny{$f})) {
	    &db_slett($db,$tabell,$felt[0],$f);
	}
    }
}

sub db_manipulate {
    my $db = $_[0];
    my $slett = $_[1];
    my $tabell = $_[2];
    my @felt = @{$_[3]};
    my @ny = @{$_[4]};
    my @gammel = @{$_[5]};
    my $en = $_[6];
    my $to = $_[7];
    my $tre = $_[8];

    my @where;

    if($en) {
	$where[0] = "$felt[1] = \'$en\' ";
    }
    if($to) {
	$where[1] = "$felt[2] = \'$to\' ";
    }
    if($tre) {
	$where[2] = "$felt[3] = \'$tre\' ";
    }

    my $where = " ".join("AND ",@where);

#	print "til: $ny[3] & fra: $gammel[3] $where\n";


    if($gammel[1]) {
	for my $i (0..$#felt ) {
#	    print "-$i|$gammel[$i]|$ny[$i]|";
#	    if(defined( $gammel[$i] ) && defined( $ny[$i] )){
#	    print "FELT til: $ny[$i] & fra: $gammel[$i] $where\n";
		&db_update($db,$tabell,$felt[$i],$gammel[$i],$ny[$i],$where);

#	    }
	}
#	print "\n";
    } else {
	&db_logg_insert($db,$tabell,\@felt,\@ny);
    }

    if($slett == 1){
	unless($ny[1]) {
	    &db_delete($db,$tabell,$where);
	}
    }
}

#for fil og db-sammenlikning
sub db_endring_med_sletting {
    my ($db,$fil,$tabell,$felt) = @_;
    my @felt = split(/:/,$felt);

    my $localfil = $navdir."local/".$fil;
    my $navmefil = $navdir."navme/".$fil;
	
    my %ny;
    if(-r $navmefil){
	%ny = &fil_hent_hash($navmefil,scalar(@felt),\%ny);
    }
    if(-r $localfil){
	%ny = &fil_hent_hash($localfil,scalar(@felt),\%ny);
    }

    #leser fra database
    my %gammel = &db_hent_hash($db,"SELECT ".join(",", @felt )." FROM $tabell ORDER BY $felt[0]");
    &db_endring($db,\%ny,\%gammel,\@felt,$tabell);
    &db_sletting($db,\%ny,\%gammel,\@felt,$tabell);
}
#for fil og db-sammenlikning
sub db_endring_uten_sletting {
    my ($db,$fil,$tabell,$felt) = @_;
    my @felt = split(/:/,$felt);
    my %ny = &fil_hent($fil,scalar(@felt));
    #leser fra database
    my %gammel = &db_hent_hash($db,"SELECT ".join(",", @felt )." FROM $tabell ORDER BY $felt[0]");

    &db_endring($db,\%ny,\%gammel,\@felt,$tabell);
}

sub db_endring {

    my $db = $_[0];
    my %ny = %{$_[1]};
    my %gammel = %{$_[2]};
    my @felt = @{$_[3]};
    my $tabell = $_[4];
    for my $feltnull (keys %ny) {
	&db_endring_per_linje($db,\@{$ny{$feltnull}},\@{$gammel{$feltnull}},\@felt,$tabell,$feltnull);
    }
}

sub db_endring_per_linje {
    my $db = $_[0];
    my @ny = @{$_[1]};
    my @gammel = @{$_[2]};
    my @felt = @{$_[3]};
    my $tabell = $_[4];
    my $id = $_[5];
    
    #eksisterer i databasen?
    if($gammel[0]) {
#-----------------------
#UPDATE
	for my $i (0..$#felt ) {
	    if(defined( $gammel[$i] ) && defined( $ny[$i] )){
#		print "NY: $ny[$i] GAMMEL: $gammel[$i]\n";
		unless($ny[$i] eq $gammel[$i]) {
		    #oppdatereringer til null m� ha egen sp�rring
		    if ($ny[$i] eq "" && $gammel[$i] ne ""){
			&db_oppdater($db,$tabell,$felt[$i],$gammel[$i],"null",$felt[0],$id);
		    } else {
			
			&db_oppdater($db,$tabell,$felt[$i],"\'$gammel[$i]\'","\'$ny[$i]\'",$felt[0],$id);
		    }
		}
	    }
	}
    }else{
#-----------------------
#INSERT
	&db_sett_inn($db,$tabell,join(":",@felt),join(":",@ny));
	
    }
}
sub db_alt_per_linje_idant_to {
    my $db = $_[0];
    my @ny = @{$_[1]};
    my @gammel = @{$_[2]};
    my @felt = @{$_[3]};
    my $tabell = $_[4];
    my $nokkel1 = $_[5];
    my $nokkel2 = $_[6];
    my $id1 = $_[7];
    my $id2 = $_[8];
    
    #eksisterer i databasen?
    if($gammel[0]) {
#-----------------------
#UPDATE
	for my $i (0..$#felt ) {
	    if(defined( $gammel[$i] ) && defined( $ny[$i] )){
		unless($ny[$i] eq $gammel[$i]) {
		    #oppdatereringer til null m� ha egen sp�rring
		    if ($ny[$i] eq "" && $gammel[$i] ne ""){
			&db_oppdater_idant_to($db,$tabell,$felt[$i],$gammel[$i],"null",$nokkel1,$nokkel2,$id1,$id2);
		    } else {
			
			&db_oppdate_idant_to($db,$tabell,$felt[$i],"\'$gammel[$i]\'","\'$ny[$i]\'",$nokkel1,$nokkel2,$id1,$id2);
		    }
		}
	    }
	}
    }else{
#-----------------------
#INSERT
	&db_sett_inn($db,$tabell,join(":",@felt),join(":",@ny));
	
    }
#-----------------------
#DELETE
    unless($ny[0]) {
	&db_slett_idant_to($db,$tabell,$nokkel1,$nokkel2,$id1,$id2);
    }
}

sub db_alt{
    my $db = $_[0];
    my $niv = $_[1]; #niv� av hashing
    my $slett = $_[2];
    my $tabell = $_[3];
    my @felt = @{$_[4]};
    my %ny = %{$_[5]};
    my %gammel = %{$_[6]};
    my @keys = @{$_[7]};
#    my @required = @{$_[8]}; #kommer med i ny databasemetode seinere. denne skal v�re med for � sjekke konsistens. not-null-felter skal v�re listet opp her.

    if($niv == 3){ 
	for my $key1 ( keys %ny ) {
	    for my $key2 (keys %{$ny{$key1}}) {
		for my $key3 (keys %{$ny{$key1}{$key2}}) {
#		my @nyrad = @{$ny{$key1}{$key2}{$key3}};
#		my @gammelrad = @{$gammel{$key1}{$key2}{$key3}};
		    my $where = &lag_where(\@felt,\@keys,[$key1,$key2,$key3]);
		    if(exists $gammel{$key1}{$key2}{$key3}) {
			for my $i (0..$#felt ) {
			    &db_update($db,$tabell,$felt[$i],$gammel{$key1}{$key2}{$key3}[$i],$ny{$key1}{$key2}{$key3}[$i],$where);
			}
		    } else {
			&db_logg_insert($db,$tabell,\@felt,\@{$ny{$key1}{$key2}{$key3}});
		    }
		}
	    }
	}
	for my $key1 ( keys %gammel ) {
	    for my $key2 (keys %{$gammel{$key1}}) {
		for my $key3 (keys %{$gammel{$key1}{$key2}}) {
		    if($slett == 1){
#		    my @nyrad = @{$ny{$key1}{$key2}{$key3}};
#		    my @gammelrad = @{$gammel{$key1}{$key2}{$key3}};
			unless($ny{$key1}{$key2}{$key3}[1]) {
			    my $where = &lag_where(\@felt,\@keys,[$key1,$key2,$key3]);
			    &db_delete($db,$tabell,$where);
			}
		    }
		}
	    }
	}
    } elsif ($niv == 2){
	for my $key1 ( keys %ny ) {
	    for my $key2 (keys %{$ny{$key1}}) {
		my $where = &lag_where(\@felt,\@keys,[$key1,$key2]);
		if(exists $gammel{$key1}{$key2}) {
		    for my $i (0..$#felt ) {
			&db_update($db,$tabell,$felt[$i],$gammel{$key1}{$key2}[$i],$ny{$key1}{$key2}[$i],$where);
		    }
		} else {
		    &db_logg_insert($db,$tabell,\@felt,\@{$ny{$key1}{$key2}});
		}
	    }
	}	
	for my $key1 ( keys %gammel ) {
	    for my $key2 (keys %{$gammel{$key1}}) {
		if($slett == 1){
		    unless($ny{$key1}{$key2}[1]) {
			my $where = &lag_where(\@felt,\@keys,[$key1,$key2]);
			if($gammel{$key1}{$key2}[1]){
			    &db_delete($db,$tabell,$where);
			}
		    }
		}
	    }
	}
    } elsif ($niv == 1){
	for my $key1 ( keys %ny ) {
	    my $where = &lag_where(\@felt,\@keys,[$key1]);
	    if(exists $gammel{$key1}) {
		for my $i (0..$#felt ) {
		    &db_update($db,$tabell,$felt[$i],$gammel{$key1}[$i],$ny{$key1}[$i],$where);
		}
	    } else {
		&db_logg_insert($db,$tabell,\@felt,\@{$ny{$key1}});
	    }
	}
    	
	for my $key1 ( keys %gammel ) {
	    if($slett == 1){
		unless($ny{$key1}[1]) {
		    my $where = &lag_where(\@felt,\@keys,[$key1]);
		    if($gammel{$key1}[1]){
			&db_delete($db,$tabell,$where);
		    }
		}
	    }
	}
	
    }
}
sub lag_where{
    my @felt = @{$_[0]};
    my @keys = @{$_[1]};
    my @vals = @{$_[2]};

    my @where;
    if (defined($vals[0])){
	if($vals[0] eq ''){
	    $where[0] = $felt[$keys[0]]." is null ";
	} else {
	    $where[0] = $felt[$keys[0]]." = \'".$vals[0]."\' ";
	}
    }
    if (defined($vals[1])){
	if($vals[1] eq ''){
	    $where[1] = $felt[$keys[1]]." is null ";
	} else {
	    $where[1] = $felt[$keys[1]]." = \'".$vals[1]."\' ";
	}
    }
    if (defined($vals[2])){
	if($vals[2] eq ''){
	    $where[2] = $felt[$keys[2]]." is null ";
	} else {
	    $where[2] = $felt[$keys[2]]." = \'".$vals[2]."\' ";
	}
    }
    my $where = " ".join("AND ",@where);
    return $where;
}

sub db_alt_per_linje {
    my $db = $_[0];
    my @ny = @{$_[1]};
    my @gammel = @{$_[2]};
    my @felt = @{$_[3]};
    my $tabell = $_[4];
    my $id = $_[5];
    
    #eksisterer i databasen?
    if($gammel[0]) {
#-----------------------
#UPDATE
	for my $i (0..$#felt ) {
	    if(defined( $gammel[$i] ) && defined( $ny[$i] )){
		unless($ny[$i] eq $gammel[$i]) {
		    #oppdatereringer til null m� ha egen sp�rring
		    if ($ny[$i] eq "" && $gammel[$i] ne ""){
			&db_oppdater($db,$tabell,$felt[$i],$gammel[$i],"null",$felt[0],$id);
		    } else {
			
			&db_oppdater($db,$tabell,$felt[$i],"\'$gammel[$i]\'","\'$ny[$i]\'",$felt[0],$id);
		    }
		}
	    }
	}
    }else{
#-----------------------
#INSERT
	&db_sett_inn($db,$tabell,join(":",@felt),join(":",@ny));
	
    }
#-----------------------
#DELETE
    unless($ny[0]) {
	&db_slett($db,$tabell,$felt[0],$id);
    }
}

sub error_correct{
    my $conn = $_[0];
    my $sql = $_[1];
    my $errmsg = $_[2];
    chomp($errmsg);
    if($errmsg =~ /ERROR:  Cannot insert a duplicate key into unique index (\w+?)_/){
	if($sql =~ s/UPDATE/DELETE FROM/){
	    $sql =~ s/SET .* (WHERE)/$1/;
	    &skriv("DATABASE-ALREADY", "sql=$sql", "message=".$errmsg);
	    &db_execute($conn,$sql);
	} else {
	    &skriv("DATABASE-ALREADY", "sql=$sql", "message=".$errmsg);
	}
    } elsif ($errmsg =~ /ERROR:  value too long for type character varying\((\d+)\)/){
	my $lengde = $1;
	if($sql =~ /^UPDATE (\w+) SET (\w+)=(.*) WHERE/){
	    
	    &skriv("TEXT-TOOLONG", "table=$1","field=$2","value=$3","length=$lengde");
	    
	} else {
	      &skriv("TEXT-TOOLONG", "table=\"$sql\"","field=","value=$errmsg","length=$lengde");
	}

    } elsif ($errmsg =~ /ERROR:  ExecAppend: Fail to add null value in not null attribute (\w+)/){
	&skriv("DATABASE-NOTNULL", "sql=$sql","value=$1");
	
    } elsif ($errmsg =~ /ERROR:  \<unnamed\> referential integrity violation - key referenced from (\w+) not found in (\w+)/){
	
	my $child = $1;
	my $parent = $2;

	my $field;

	if($sql =~ /UPDATE \w+ SET (\w+)\=(.*) WHERE/){
	
	    $field = "(".$1."=".$2.")";
	}
	&skriv("DATABASE-REFERENCE", "sql=$sql","child=$child", "field=$field","parent=$parent");
	
    } else {
	&skriv("DATABASE-ERROR", "sql=$sql", "message=".$errmsg);
    }
}

sub rydd {    
    if (defined $_[0]) {
	$_ = $_[0];
	s/\'/\\\'/;
	s/\\/\\\\/;
	s/\s*$//;
	s/^\s*//;
    return $_;
    } else {
	return "";
    }
}
sub db_connect {
    my ($db,$user,$password) = @_;
    my $conn = Pg::connectdb("dbname=$db user=$user password=$password");
    die $conn->errorMessage unless PGRES_CONNECTION_OK eq $conn->status;
    return $conn;
}

sub db_readconf {
    return &hash_conf('/usr/local/nav/local/etc/conf/db.conf');
}

sub db_get {
    my $myself = $_[0];

    my %hash = &db_readconf();
			
    my $db_user = $hash{'script_'.$myself};
    my $db_passwd = $hash{'userpw_'.$db_user};
    my $db_db = $hash{'db_'.$db_user};
    my $db_host = $hash{'dbhost'};
    my $db_port = $hash{'dbport'};
						    
    my $conn = Pg::connectdb("host=$db_host port=$db_port dbname=$db_db user=$db_user password=$db_passwd");
    die $conn->errorMessage unless PGRES_CONNECTION_OK eq $conn->status;
    return $conn;
}
sub db_select {
    my $sql = $_[1];
    my $conn = $_[0];
    my $resultat = $conn->exec($sql);
    unless ($resultat->resultStatus eq PGRES_TUPLES_OK){
	&skriv("DATABASE-ERROR", "sql=$sql", "message=".$conn->errorMessage);
    }
    return $resultat;
}
sub db_execute {
    my $sql = $_[1];
    my $conn = $_[0];
    my $resultat = $conn->exec($sql);
    unless ($resultat->resultStatus eq PGRES_COMMAND_OK){
	&error_correct($conn,$sql,$conn->errorMessage);
	return 0;
#	&skriv("DATABASE-ERROR", "sql=$sql", "message=".$conn->errorMessage);
    }
    return 1;
}

return 1;
