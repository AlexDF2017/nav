<?php

include('formatting.inc.php');
include('access.inc.php');
include('file.inc.php');

list($lock,$user) = locked($file);

if(!isset($file)){
  header("Location: index.php");
} elseif($lock) {
  //l�st allerede, ikke pr�v � l�se.
  header("Location: view.php?file=$file");
  exit;
} else {
  //pr�ver � l�se
  //print $file;
  shell_exec('/usr/bin/co -l 2>&1 '.path_file($file));
  clearstatcache();
  $owner = locked_rcs($file);
  //print "|".$owner."|";
  if(locked_rcs($file) == user_web()){ //apache eier fila.
    //nrs_l�s
    if(!locked_nrs($file)){
      if (!lock_nrs($file)){
	die("0018: feil under nrs-l�sing");
      } else {
	copy(path_file($file),path_nrt($file));
      }
    }
  } else {
    /*    if(locked_rcs($file) == user_web()){
      if(!locked_nrs($file)){
	if (!lock_nrs($file)){
	  die("0018: feil under nrs-l�sing");
	} else {
	  copy(path_file($file),path_nrt($file));
	}
      }
    } else {
    */
      print "En mystisk feil har skjedd. Clearstatcache virket ikke.";
    
    //har ikke rukket � l�se fila enda
    //print user_res();
    /*print locked_rcs($file);
  print "!=";
  print user_web();
  //die("l�sefeil");*/
  }
  header("Location: view.php?file=$file");
  exit;
}

?>
