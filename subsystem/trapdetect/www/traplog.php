<?php require('include.inc'); ?>

<?php tittel("Hovedlogg") ?>

Hovedloggen som logger all aktivitet. Output og kommentarer fra hovedprogram.

<?php topptabell(logg) ?>

<p><center><h3><u>Dagens logg</u></h3></center></p>

<?php

echo "<form action=traplog.php method=\"GET\">\n";
if ($sokeord) {
  echo "S�k p� ord: <input type=text name=sokeord value=$sokeord>\n";
} else {
  echo "S�k p� ord: <input type=text name=sokeord>\n";
}
echo "<input type=submit>\n";
echo "</form>\n";

$filename = "../log/traplog";
$innhold = file($filename);

function tell_linjer($innhold) {
  $innlegg = 0;
  $teller = 0;
  while($innhold[$teller]) {
    if (preg_match("/^-/i", $innhold[$teller])) {
      $innlegg++;
    }
    $teller++;
  }
  return $innlegg;
}

function skrivalt($innhold) {
  $teller = 0;
  while($innhold[$teller]) {
    print "$innhold[$teller]<br>\n";
    $teller++;
  }
}

function hentsokeord($array, $sokeord) {
  $teller = 0;
  $innlegg = 0;
  $ord = 0;
  $mulig = 0;

  $sokeord = preg_replace("/\//", "\/", $sokeord);

  while($array[$teller]) {
    if (((preg_match("/\d+\/\d+\/\d+/i", $array[$teller])) && !($mulig))) {
      $start = $teller;
      $mulig = 1;
      if (preg_match("/$sokeord/i", $array[$teller])) {
	$ord = 1;
      } else {
	$ord = 0;
      }
    } elseif (($mulig) && (preg_match("/$sokeord/i", $array[$teller]))) {
      $ord = 1;
    } elseif ((preg_match("/^-/i", $array[$teller])) && ($mulig) && ($ord)) {
      $innlegg++;
      for ($i = $start; $i <= $teller; $i++) {
	$streng .= "$array[$i]<br>\n";
      }
      $mulig = 0;
      $start = 0;
      $ord = 0;
    } elseif ((preg_match("/^-/i", $array[$teller])) && ($mulig)) {
      $mulig = 0;
    }
    $teller++;
  }
  return array ($innlegg, $streng);
}

if ($sokeord) {
  list ($antall, $streng) = hentsokeord($innhold, $sokeord);
  print "<b>Antall innlegg: $antall</b><br><br>\n";
  print "$streng<br>\n";
} else {
  $antall = tell_linjer($innhold);
  print "<b>Antall innlegg: $antall</b><br><br>\n";
  skrivalt($innhold);
}

?>

<?php bunntabell() ?>
