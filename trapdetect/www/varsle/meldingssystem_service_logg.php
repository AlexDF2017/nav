<?php
require ('meldingssystem.inc');
html_topp('Servicelogg');

list ($bruker,$admin) = verify_user($bruker,$REMOTE_USER);
if ($admin && $REMOTE_USER != $bruker) {
  print "Du er innlogget som <b>$bruker</b> med administratorrettighetene til <b>$REMOTE_USER</b><br>\n";
}

print "<h3>Servicelogg</h3>";
print "<p>Oversikt over hvem som har satt enheter av og p� service.</p>";

print "<hr width=450 align=left>\n";
$fcontents = file ('servicelogg');
while (list ($line_num, $line) = each ($fcontents)) {
    echo "$line<br>\n";
}
print "<hr width=450 align=left>\n";
print "<p>";
knapp_hovedside($bruker);
print "</p>\n";

?>

</body></html>