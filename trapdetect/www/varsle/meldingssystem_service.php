<!-- F�r inn disse variable:
eier: kan v�re flere variable
trap: sier seg selv
bruker: brukernavn p� han som er p�
-->

<?php
require ('meldingssystem.inc');
html_topp('Sett p� service');

list ($bruker,$admin) = verify_user($bruker,$REMOTE_USER);
if ($admin && $REMOTE_USER != $bruker) {
  print "Du er innlogget som <b>$bruker</b> med administratorrettighetene til <b>$REMOTE_USER</b><br>\n";
}

$border=0;
$temp = $HTTP_POST_VARS;

$enheterav = finn_enheter('t', $bruker);
$enheterpa = finn_enheter('f', $bruker);

print "<p><h3>Sett p� service</h3>Her er oversikt over alle enheter du har mulighet til � sette p� service. I tabellen til venstre kan du merke de enhetene du vil sette P� service. I tabellen til h�yre kan du merke de enhetene du vil TA AV service. Trykk s� <b>OK</b></p>";

# Knapp til loggen
print "<form action=meldingssystem_service_logg.php method=POST>";
print "<input type=hidden name=bruker value=$bruker>";
print "<input type=submit value=\"Logg\">\n";
print "</form>\n";

knapp_hovedside($bruker);

##############################
# Kobler til database
##############################
$dbh = pg_Connect ("dbname=trapdetect user=varsle password=lgagikk5p");
$dbh_m = pg_Connect ("dbname=manage user=navall password=uka97urgf");

$antall_enheter = sizeof($enheterpa) + sizeof($enheterav);
echo "Det er totalt $antall_enheter enheter tilgjengelig for bruker <b>$bruker</b><br>\n";

##################################################
# Skriver ut alle enhetene og merker dem som
# allerede er p� service.
##################################################
echo "<form action=meldingssystem_service_sett.php method=\"POST\">";
echo "\n<table width=90%  cellpadding=3 border=$border>";
echo "<tr><td>Enheter ikke p� service</td><td>Enheter p� service</td></tr><tr><td>\n";

# Enheter som ikke er p� service

echo "<select name=enheterav[] multiple size=20>\n";

$temp = array_keys($enheterav);
sort ($temp);
foreach ($temp as $enhet) {
  echo "<option>$enhet</option>\n";
}
echo "</select>\n";

# Enheter som er p� service

echo "</td><td>\n";
echo "<select name=enheterpa[] multiple size=20>\n";

$temp = array_keys($enheterpa);
sort ($temp);
$antallpa = sizeof($temp);
if ($antallpa == 0) {
  echo "<option>Ingen</option>";
} else {
  foreach ($temp as $enhet) {
    echo "<option>$enhet</option>\n";
  }
}
echo "</select>\n";

echo "</td></tr>\n";
echo "</table>\n";

# Tabell ferdig

echo "<input type=hidden name=bruker value=$bruker>\n";
echo "<input type=submit value=\"OK\">";
echo "</form>\n";

# Stygg m�te � resette p�...
echo "<form action=meldingssystem_service.php method=\"POST\">";
echo "<input type=hidden name=bruker value=$bruker>\n";
echo "<input type=submit value=Reset>";
echo "</form>";

########################################
# Henter alle bokser som er p�/av service
########################################
function finn_enheter($bol, $bruker) {
  $array = array();
  $dbh = pg_Connect ("dbname=trapdetect user=varsle password=lgagikk5p");
  $dbh_m = pg_Connect ("dbname=manage user=navall password=uka97urgf");

  # Henter eierforhold
  $sporring = "select o.navn from bruker b, brukeriorg bio, org o where b.bruker='$bruker' and b.id=bio.brukerid and bio.orgid=o.id";
  $res = pg_exec($dbh,$sporring);
  $antall = pg_numrows($res);

  # Lager del-sp�rring ut fra hvor mange org bruker er medlem i.
  # Delsp�rring blir lagret i $temp.
  $temp = "";
  for ($i=0;$i<$antall;$i++) {
    $row = pg_fetch_array($res,$i);
    if ($i<$antall-1) {
      $temp .= "orgid='".strtolower($row[0])."' or ";
    } else {
      $temp .= "orgid='".strtolower($row[0])."'";
    }
  }

  # Lager selve sp�rringen.
  $sporring;
  if ($bol == 'f') {
    $sporring = "select sysname,kat from boks where active='f' and ($temp)";
  } elseif ($bol == 't') {
    $sporring = "select sysname,kat from boks where active='t' and ($temp)";
  } else {
    print "Ingen kjente boolske verdier<br>";
  }

  $result = pg_exec($dbh_m,$sporring);
  $rows = pg_numrows($result);

  for ($i=0;$i<$rows;$i++) {
    $rad = pg_fetch_row($result,$i);
    $array[$rad[0]] = $rad[1];
  }
  return $array;
}


?>

</body></html>
