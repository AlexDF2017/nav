<?php
$test = fopen("test.txt","w");
fwrite($test,date("i:s "));

# preset

$grense = 200; # treff per side

############
## Databasetilkobling
############
    $db = pg_Connect("dbname=manage user=navall password=uka97urgf");

$fil = les_fil("/usr/local/nav/local/etc/conf/ragen/ragen.conf","r");
$fil .= les_fil("/usr/local/nav/navme/etc/conf/ragen/ragen.conf","r");

$allowed = verify();
list($filparam,$urlparam,$navnparam,$forklar) = tolk_fil($fil,$rapport,$allowed);

//print $filparam[skjul];
//    print $QUERY_STRING;

$sql = $filparam[sql];
if(!$sql){
    $overskrift="Det fins ikke en definert rapport for $rapport";
}
$ar_where = array();
//print $sql;
if($sql){
if(preg_match("/SELECT(.*)FROM/is",$sql,$sel)) {
//    print $sel[1];
    $sel[1] = preg_replace("/\,\s+/",",",$sel[1]);//fjerner mellomrom etter komma
    $sel[1] = preg_replace("/^\s+/","",$sel[1]);//fjerner startende mellomrom
	$sel[1] = preg_replace("/\s+$/","",$sel[1]);
    $select = split(",",$sel[1]);
    $urlselect = $select;
    for($i=0;$i<sizeof($urlselect);$i++){
	//print $urlselect[$i];
	if(preg_match("/\ AS\ (\w+)/i",$urlselect[$i],$nysel)){
	    $urlselect[$i]=$nysel[1];
	} elseif(preg_match("/\.(\w+)/",$urlselect[$i],$nysel)){
	    $urlselect[$i]=$nysel[1];
	}
	$fraselect[$urlselect[$i]] = $i;
	if($$urlselect[$i]){
	    //print $$urlselect[$i];
	    $verdi =  $$urlselect[$i];
	    array_push($ar_where,"$select[$i] like '$verdi'");
	//print $urlselect[$i];
	}
    }
}
if(preg_match("/FROM(.*?)(?:WHERE|ORDER|GROUP|LIMIT|$)/is",$sql,$sel)) {
    //$sel[1] = preg_replace("/\s/","",$sel[1]); blir bare feil her
    $ar_from = split(",",$sel[1]);
}
if(preg_match("/WHERE(.*?)(?:ORDER|GROUP|LIMIT|$)/is",$sql,$sel)) {
    $ar_where = array_merge($ar_where,preg_split("/and/i",$sel[1]));
}
if(preg_match("/GROUP\ BY(.*?)(?:ORDER|LIMIT|$)/is",$sql,$sel)) {
//    print $sel[1];
    $ar_group_by = split(",",$sel[1]);
}
if(preg_match("/ORDER\ BY(.*?)(?:GROUP|LIMIT|$)/is",$sql,$sel)) {
    //print $sel;
    $ar_order_by = split(",",$sel[1]);
}

    //print sizeof($ar_order_by);

if($limit){
#	     print "hadde limit fra f�r";
    $ar_limit = split(",",$limit);
} elseif(preg_match("/LIMIT(.*?)$/is",$sql,$sel)){
    $ar_limit = split(",",$sel[1]);
}

$har_from = join(",",$ar_from);
$sql2 = "SELECT ".join(",",$select)." FROM ".$har_from;
$sql_antall = "SELECT $select[0] FROM ".$har_from;
if($ar_where){
    $har_where = " WHERE ".join(" AND ",$ar_where);
    $sql2 .= $har_where;
    $sql_antall .= $har_where;
} else {
    $har_where = " ";
}
if($ar_group_by){
    $har_group_by = " GROUP BY ".join(",",$ar_group_by);
    $sql2 .= $har_group_by;
    $sql_antall .= $har_group_by;
} else {
    $har_group_by = " ";
}

if(!$ar_order_by){
    $ar_order_by = array();
    if($order_by){
	array_push($ar_order_by,$order_by);
    }
    if($filparam[order_by]){
	array_push($ar_order_by,$filparam[order_by]);
    }
}

if($ar_order_by){
    $sql2 .= " ORDER BY ".join(",",$ar_order_by);
}

if($limit){
    $ar_limit = split(",",$limit);
    //@limit = map rydd($_),@limit;
} else {
    $ar_limit = array($grense,0);
}
$sql2.= " LIMIT ".join(",",$ar_limit);
//print $sql_antall;
$sql = $sql2;

fwrite($test,"\nlimit ".date("i:s "));

$tabell = db_2d_array($db,$sql);
$antall_rader = db_antall($db,$sql_antall);

if($filparam[ekstra]) {
    $ekstra_kolonner = split(",",$filparam[ekstra]);
    $urlselect = array_merge($urlselect,$ekstra_kolonner);
    for ($i = 0; $i<sizeof($tabell);$i++ ) {
   	$rad = $tabell[$i];
	$tabell[$i] = array_merge($rad,$ekstra_kolonner);
    }
}    
if($filparam[skjul]) {
//    print "ja";
    $skjul = split(",",$filparam[skjul]);
    for($i=0;$i<sizeof($urlselect);$i++){
//	print $urlselect[$i];
	if($fraselect[$skjul[$i]]){
//	    print $fraselect[$skjul[$i]];
	    //unset($rad[$fraselect[$skul_kolonner[$i]]]);
	    $skjulte_kolonner[$fraselect[$skjul[$i]]] = 1;
	}
    }
}
if($filparam[count]){
    $opptelling = split(",",$filparam[count]);
    foreach(array_keys($opptelling) as $o){
	$opptell[$o] = "count(".$opptelling[$o].")";
    }
    $sql_count = "select ".join(", ",$opptell)." from ".$har_from.$har_where.$har_group_by;
    $resultatet = db_1d_array($db,$sql_count);
    foreach(array_keys($urlselect) as $u) {
	if($resultatet[$u]){
	    $count_cols[$fraselect[$opptelling[$u]]] = $resultatet[$u];
	}
    }
}
if($filparam[sum]){
    $opptelling = split(",",$filparam[sum]);
    foreach(array_keys($opptelling) as $o){
	$opptell[$o] = "sum(".$opptelling[$o].")";
    }
    $sql_sum = "select ".join(", ",$opptell)." from ".$har_from.$har_where.$har_group_by;
    $resultatet = db_1d_array($db,$sql_sum);
    foreach(array_keys($urlselect) as $u) {
	if($resultatet[$u]){
	    $sum_cols[$fraselect[$opptelling[$u]]] = $resultatet[$u];
	}
    }
}
if(count($forklar)){
    foreach(array_keys($forklar) as $key){
	$forklartekst.="| &quot;".$key."&quot; = ".$forklar[$key]." ";
    }
$forklartekst = "<font size=\"1\">".$forklartekst." |</font>";
}

} //close if $sql

fwrite($test,"\nf�r skjerm ".date("i:s "));
#############
## Skriving til skjerm
#############
    print topp($rapport);
print "<table border=\"0\" cellspacing=\"0\" cellpadding=\"0\"><tr><td><table border=\"0\" cellspacing=\"0\" cellpadding=\"0\" width=\"100%\"><tr><td background=\"bakgrunn_nav.php\" align=\"left\">";
if(!$overskrift){
    $overskrift = $filparam[overskrift];
}
if(!$overskrift){
    $overskrift = $rapport;
}
$overskrift = $overskrift;
$peker = lag_peker($urlselect,$QUERY_STRING); // tar vare p� sidevariablene til neste side

print "<img ".skriv_bilde($overskrift,"overskrift")." border=\"0\">";
//src=\"overskrift.php?overskrift=$overskrift\"
print "</td><td background=\"bakgrunn_nav.php\" valign=\"bottom\" align=\"right\"><font color=\"#ffffff\"><img src=\"bildetekst.php?tekst=".date("j.n.Y")."\"  border=\"0\"></font>";



## husker gammel querystring
if($begrenset){
    $skjemalink = "<form action=\"?$peker&begrenset=0\" method=\"post\"><td valign=\"top\"><hidden name=\"begrenset\" value=\"0\"><input type=\"image\" ".skriv_bilde("Skjul_skjema")." border=\"0\"></td></form>";
} else {
    $skjemalink = "<form action=\"?$peker&begrenset=1\" method=\"post\"><td valign=\"top\"><hidden name=\"begrenset\" value=\"1\"><input type=\"image\" ".skriv_bilde("S�keskjema")." border=\"0\"></td></form>";
}
print "<table><tr><td valign=\"top\"><a href=\"reports.php\"><img ".skriv_bilde("Hjem"). "border=\"0\"\"></a></td>".$skjemalink."</tr></table></td></tr></table>";

if($begrenset){
//skriv_skjemainnhold
//kan ikke kommenteres bort, da ingen vet hva variablene heter

    skriv_skjemainnhold($urlselect,$navnparam,$rapport,$skjulte_kolonner);
}

print forrigeneste($ar_limit,$peker,$antall_rader,$grense);
print $forklartekst;

if($antall_rader){
    skriv_tabell($tabell,$urlparam,$urlselect,$fraselect,$navnparam,$rapport,$skjulte_kolonner,$count_cols,$sum_cols);
}

print tabell_bunn();
print forrigeneste($ar_limit,$peker,$antall_rader,$grense);
print debug_sql($sql);
pg_close($db);

/*
skrivhash($filparam);
skrivhash($urlparam);
skrivhash($navnparam);
skrivhash($select);
skrivhash($where);
skrivhash($from);
skrivhash($order_by);
*/

    print "</td></tr></table></html>";
fwrite($test,"etter skjerm ".date("i:s "));

function topp($rapport="") {
    return "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.01 Transitional//EN\"><html><head><link rel=\"STYLESHEET\" type=\"text/css\" href=\"stil.css\"><title>NAV::ragen::$rapport</title></head><body  bgcolor=\"#ffffff\" text=\"#000000\" link=\"#000099\" alink=\"#0000ff\" vlink=\"#000099\">";
    }
function verify(){
    global $PHP_AUTH_USER;
    $passordfil = "/usr/local/nav/local/apache/htpasswd/.htpasswd-sec";
    $fd = fopen ($passordfil,"r");
    $funnet = 0;
    while (!$funnet&&!feof($fd)) {
	$buffer = fgets($fd, 4096);
	if(preg_match("/^$PHP_AUTH_USER\:/i",$buffer)){
	    $funnet = 1;
	}
    }
    fclose ($fd);
    return $funnet;
}


function skrivhash($hash){
########
## Tar inn en hash og skriver den som en htmltabell
########
    if($hash){
	print "<table border>";
	foreach ($hash as $key => $value) {
	    print "<tr><td>|$key|</td><td>|$value|</td></tr>";
	}
	print "</table>";
    }
}
function tolk_fil($fil,$rapport,$allowed=0){
#############
## Behandler tekststreng og putter inn i hasher
#############
    global $test;
fwrite($test,"1: ".date("i:s "));
    if($allowed){
	if(preg_match("/^\s*$rapport(?:\_sec)?\s*{(.*?)}/sm",$fil,$regs)){
	    $var = $regs[1];
	    //print $var;
	    preg_match_all("/^\#{0}\s*\\\$(\S+?)\s*=\W*\"(.+?)\"\s*\;/smi",$var,$para);
	    for ($i = 0; $i<sizeof($para[0]); $i++) {
		$key = $para[1][$i];
		$value = $para[2][$i];
		$filparam[$key] = $value;
		//echo "<br>".$key." = ".$value;
		if(preg_match("/url_(\S+)/i",$key,$newkey)){
		    $urlparam[$newkey[1]] = $value;
		    //print $newkey[1];
		} elseif(preg_match("/navn_(\S+)/i",$key,$newkey)) {
		    $navnparam[$newkey[1]] = $value;
		    //print $newkey[1];
		} elseif(preg_match("/forklar_(\S+)/i",$key,$newkey)) {
		    $forklar[$newkey[1]] = $value;
		}

	    }
	}
    } else {
	if(preg_match("/^\s*$rapport\s*{(.*?)}/sm",$fil,$regs)){
	    $var = $regs[1];
	    //print $var;
	    preg_match_all("/\#{0}\s*\\\$(\S+?)\s*=\W*\"(.+?)\"\s*\;/smi",$var,$para);
	    for ($i = 0; $i<sizeof($para[0]); $i++) {
		$key = $para[1][$i];
		$value = $para[2][$i];
		$filparam[$key] = $value;
		//echo "<br>".$key." = ".$value;
		if(preg_match("/url_(\S+)/i",$key,$newkey)){
		    $urlparam[$newkey[1]] = $value;
		    //print $newkey[1];
		} elseif(preg_match("/navn_(\S+)/i",$key,$newkey)) {
		    $navnparam[$newkey[1]] = $value;
		    //print $newkey[1];
		} elseif(preg_match("/forklar_(\S+)/i",$key,$newkey)) {
		    $forklar[$newkey[1]] = $value;
		}
	    }
	    
	}
    }
fwrite($test,"3: ".date("i:s "));

    return array($filparam,$urlparam,$navnparam,$forklar);
}

function forrigeneste($sql_limit,$peker,$antall,$grense=200){
    /*
	sql_limit = limit-delen av sql-kallet (array)
	peker     = generell peker som alltid m� bli lagt til lenkene til ragen
	antall    = antall rader returnert fra databasen
	grense    = forh�ndsdefinert grense for hvor mange treff som skal vises per side
	    */

    $neste = $sql_limit[1]+$grense;
    $forrige = $sql_limit[1]-$grense;
    $fra = $sql_limit[1] +1;
    $til = $sql_limit[1] + $sql_limit[0];
    
    if($sql_limit[1]){ 
	$forrigelink = "<a href=\"?$peker&limit=".$sql_limit[0]."%2c".$forrige."\">Forrige</a> ";
    } else {
	$forrigelink = "&nbsp;";
    }
    
    if($sql_limit[0]+$sql_limit[1]<$antall){
	$nestelink = " <a href=\"?$peker&limit=".$sql_limit[0]."%2c".$neste."\">Neste</a>";
    } else {
	$nestelink = "&nbsp;";
    }
    
    if($antall){
	if($grense>$antall){
	    $treff = "Totalt $antall treff i databasen";
	} elseif ($til>$antall){
	    $treff = "Viser n� treff $fra til $antall av totalt $antall treff i databasen";
	} else {
	    $treff = "Viser n� treff $fra til $til av totalt $antall treff i databasen";
	}
    } else {
	$treff = "Dette ga null treff i databasen";
    }
    
    return "<table border=\"0\" cellspacing=\"0\" cellpadding=\"0\" width=\"100%\"><tr><td align=\"left\" width=\"100\">".$forrigelink."</td><td align=\"center\">".$treff."</td><td align=\"right\" width=\"100\">".$nestelink."</td></tr></table>";

}

//phpinfo();

function les_fil($fil,$var){
##############
## Leser fra fil til en lang tekstreng
##############
    $filinnhold = "";
    if(is_readable($fil)){
	$fp = fopen($fil,$var);
	$filinnhold = fread($fp,filesize($fil));
	fclose($fp);
    }
    return $filinnhold;
}

function db_antall($db,$sql) {
    $res = pg_exec($db,$sql);
    return pg_numrows($res);
}
function db_1d_array($db,$sql){
    $res = pg_exec($db,$sql);
    return pg_fetch_row($res,0);
}

function db_2d_array($db,$sql){
    $res = pg_exec($db,$sql);
    $rader = pg_numrows($res);
    $resultat = array();
    for ($i=0;$i<$rader;$i++){
	$resultat[$i] = pg_fetch_row($res,$i);
    }
    return $resultat;
}
function lag_peker($urlselect,$querystring){
    $peker = $querystring;
    for($i=0;$i<sizeof($urlselect);$i++) {
		$this = $urlselect[$i];
		global $$this;
		$that = $$this;
		if($that){
		    $peker .= "&$this=$that";
		}
	    }
    return $peker;
}

function skriv_skjemainnhold($urlselect,$navnparam,$rapport,$skjulte_kolonner){
    print "<table border=\"0\" cellspacing=\"0\" cellpadding=\"0\" width=\"600\" align=\"center\"><tr><td><form action=\"?rapport=$rapport\" method=\"get\"><input type=\"hidden\" name=\"rapport\" value=\"".$rapport."\"><table border=\"0\" cellspacing=\"0\" cellpadding=\"0\">";
    for($i=0;$i<sizeof($urlselect);$i++) {
	//if(!$skjulte_kolonner[$i]){
		$this = $urlselect[$i];
		print "<tr><td background=\"bakgrunn_nav.php\">";
//<font color=\"#ffffff\">";
		if($navnparam[$this]){
		    $tekst = $navnparam[$this];
		} else {
		    $tekst = $this;
		}
		print "<img ".skriv_bilde($tekst)." border=\"0\"></td>";

	   // }
	global $$this;
	$skjemaverdi = $$this;
	
	 print "<td><input type=\"text\" name=\"$this\" value=\"$skjemaverdi\"></td></tr>";
    }
    print "<tr><td></td><td background=\"bakgrunn_nav.php\"><input type=\"image\" ".skriv_bilde("S�k>>")." border=\"0\" name=\"send\" value=\"Send\"></td></tr></table></form></td><td><p>Fyll inn det du vil s�ke etter i �nskede felt. Du kan bruke % for wildcard.</p></td></tr></table>";
}


function skriv_tabelloverskrift($urlselect,$navnparam,$rapport,$skjulte_kolonner,$count_cols=0,$sum_cols=0) {
    print "<tr>";
    for($i=0;$i<sizeof($urlselect);$i++) {
	    if(!$skjulte_kolonner[$i]){
		$this = $urlselect[$i];
		global $QUERY_STRING;
		$peker = lag_peker($urlselect,$QUERY_STRING);
		print "<form action=\"?$peker&order_by=$this\" method=\"post\"><td bgcolor=\"#486591\">";
		if($navnparam[$this]){
		    $tekst = $navnparam[$this];
		} else {
		    $tekst = $this;
		}
		print "<input type=\"image\" ".skriv_bilde($tekst)." border=\"0\">";
		
		if($count_cols[$i]){
		    print " ".$count_cols[$i];
		}
		if($sum_cols[$i]){
		    print " ".$sum_cols[$i];
		}
		print "</td></form>";
	    }
    }
    print "</tr>";
}
function skriv_tabell($tabell,$urlparam,$urlselect,$fraselect,$navnparam,$rapport,$skjulte_kolonner,$count_cols=0,$sum_cols=0){
    print "<table border=\"0\" cellspacing=\"0\" cellpadding=\"0\" width=\"100%\">";
    $teller = 0;
    skriv_tabelloverskrift($urlselect,$navnparam,$rapport,$skjulte_kolonner,$count_cols,$sum_cols);

    for($i=0;$i<sizeof($tabell);$i++){
	$rad = $tabell[$i];
	print "<tr>";
	list($teller,$farge) = farge($teller);
	for($j=0;$j<sizeof($rad);$j++){
	    if(!$skjulte_kolonner[$j]){
		print "<td bgcolor=\"$farge\">";
		$rute = $j;
		if($link = $urlparam[$urlselect[$rute]]){
		    //print $link;
		    //$link = $urlparam[$urlselect[$rute]];
		    $res_size = preg_match_all("/\\\$(\w+)/",$link,$res);

//		    print $res[1][1];
//		    print $fraselect[$res[1][1]];
//		    print $rad[$fraselect[$res[1][1]]];

		    for($r=0;$r<$res_size+1;$r++){
			$link = str_replace("\$".$res[1][$r],$rad[$fraselect[$res[1][$r]]],$link);

		    }

//    $link = preg_replace("/(\\\$(\w+))/",$rad[$fraselect["$1"]],$link);


		    //		$link = $rad[$fraselect[$res[1]]];
		    if($link){
			print "<a href=\"$link\">";
			skriv_rute($rad[$rute]);
			print "</a>";
		    } else {
			skriv_rute($rad[$rute]);
		    }
		    
		} else {
		    skriv_rute($rad[$rute]);
		}
		print "</td>";
	    }	    
	}
	print "</tr>";
    }
    print "</table>";
}
function skriv_rute($innhold){
    if ($innhold) {
	print $innhold;
    } else {
	print "&nbsp;";
    }
}
function farge($teller) {
    if ($teller == 0) {
	return array(1,"#fafafa");
    } else {
	return array(0,"#efefef");
    }
}
function tabell_bunn(){
    return "<table border=\"0\" cellspacing=\"0\" cellpadding=\"0\" width=\"100%\"><tr><td background=\"bakgrunn_nav.php\" align=\"right\"><font color=\"#ffffff\"><a href=\"mailto:gartmann@stud.ntnu.no\"><font color=\"#ffffff\">Sigurd Gartmann</font></a>, ITEA, NTNU</font></td></tr></table>";
}

function debug_sql($sql=""){
    return "<p><font color=\"#ffffff\">".$sql."</font></p>";
}

function skriv_bilde($tekst="",$storrelse="bildetekst"){
// overskrift.php
// bildetekst.php	
    $filtekst = strtr($tekst,"��� ","aoa_");
    $filbase = "/pic/ragen/".$storrelse."/".$filtekst.".png";
$filurl = "../local/".$filbase;
$filnavn = "/usr/local/nav/local/apache/res/".$filbase;

if(!file_exists($filnavn)){

    $font = "kulfont.ttf";

    if($storrelse=="overskrift"){
	$tsize = imagettfbbox(32,0,$font,$tekst);
	$dx = abs($tsize[2]-$tsize[0]);
	$dy = abs($tsize[5]-$tsize[3]);
	$im = imagecreate ($dx+80,48); 
	$black = ImageColorAllocate ($im, 0, 0, 0); 
	$color_nav = ImageColorAllocate ($im, 71, 100, 144); 
	$color_white = ImageColorAllocate ($im, 255, 255, 255);
	imagefill($im,0,0,$color_nav);
	ImageTTFText ($im, 32, 0, 0,35, $color_white,$font,$tekst); 
	ImageTTFText ($im, 12, 0, $dx+40,$dy+5, $color_white,$font,NAV); 
	
    } else {
	$tsize = imagettfbbox(12,0,$font,$tekst);
	$dx = abs($tsize[2]-$tsize[0]);
	$dy = abs($tsize[5]-$tsize[3]);
	$im = imagecreate ($dx+3,$dy+4); 
	$black = ImageColorAllocate ($im, 0, 0, 0); 
	$color_nav = ImageColorAllocate ($im, 71, 100, 144); 
	$color_white = ImageColorAllocate ($im, 255, 255, 255);
	$tekst = ucfirst($tekst);
	imagefill($im,0,0,$color_nav);
	ImageTTFText ($im, 12, 0, 0,12, $color_white,$font,$tekst); 
	//ImageTTFText ($im, 12, 0, $dx+40,$dy+5, $color_white,$font,NAV); 
    }

    Imagepng($im,$filnavn); 
    ImageDestroy ($im);

    //    return "src=\"".$storrelse.".php?tekst=".urlencode($tekst)."\" alt=\"$tekst\"";
}
return "src=\"$filurl\" alt=\"$tekst\"";
}    
?>
