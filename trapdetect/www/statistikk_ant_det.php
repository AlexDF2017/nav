<?php require('include.inc'); ?>
<?php require('statistikk.inc'); ?>

<?php tittel("TrapDetect") ?>

Denne siden viser oversikt over hvilke enheter som har sendt ut denne trap'en. Oversikten er begrenset til � vise
antall traps, mer detaljert informasjon m� finnes p� status, eller i hendelsesregistret.

<?php topptabell(statistikk) ?>

<?php

if ($dager > 0) {
	$ar = substr($dato,-2);
	$temp = substr($dato,0,4);
	$dag = substr($temp,0,2);
	$mnd = substr($temp,-2);
	$tmpdato = date ("dmy",mktime(0,0,0,$mnd,$dag-$dager,$ar));
	echo "<center><p><h3>Antall traps mottatt fra $navn i tidsrommet $tmpdato-$dato</h3></p></center>\n";
} else {
	echo "<center><p><h3>Antall traps mottatt fra $navn den $dato</h3></p></center>\n";
}

function lagDataDettmp () {

	global $dato, $dager, $navn;

	$dbh = mysql_connect("localhost", "nett", "stotte") or die ("Kunne ikke �pne connection til databasen.");
	mysql_select_db("manage", $dbh);

	$ar = substr($dato,-2);
	$temp = substr($dato,0,4);
	$dag = substr($temp,0,2);
	$mnd = substr($temp,-2);

	$teller = 0;
	while ($teller <= $dager) {
		$dbdato = date ("Y-m-d",mktime(0,0,0,$mnd,$dag-$teller,$ar));

		$sporring = "SELECT * FROM status WHERE fra LIKE \"%".$dbdato."%\" AND trapsource=\"$navn\"";
		$result = mysql_query("$sporring", $dbh) or die ("Fikk ingenting fra databasen.");

		array ($data);

		while ($row = mysql_fetch_array ($result)) {
			$data[$row["trap"]] ++;
		}
		$teller++;
	}

	$keys = array_keys($data);
	$key = current($keys);
	$max = 0;
	while ($key) {
		if ($data[$key] > $max) { 
			$max = $data[$key];
		}
		$key = next ($keys);
	}
	return array ($data,$max);
}

	list ($data,$max) = lagDataDettmp();
	list ($imagemap, $bilde) = tegnBilde($data, $max);

	echo "<center><img src=\"gif/$bilde.gif\" usemap=\"#map\" border=0></center>";

	$antall = sizeof($imagemap);
	echo "<map name=\"map\">";
	for ($i = 0; $i < $antall; $i++) {
		$oid = key ($imagemap);
		list($x,$y,$xx,$yy) = $imagemap[$oid];
		echo "<area shape=rect href=\"statistikk_meldinger.php?name=$navn&date=$dato&antdager=$dager&oid=$oid\" coords=\"$x,$y,$xx,$yy\">\n";
		next($imagemap);
	}
	echo "</map>";
?>


<?php bunntabell() ?>
