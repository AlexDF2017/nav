<?php require('include.inc'); ?>

<?php tittel("TrapDetect") ?>

Hjelpsiden - for de trengende...

<?php topptabell(topp) ?>

<center><p><h2><u><b>TRAPDETECT</b></u></h2></p></center>

<p><h3>Bakgrunn:</h3></p>
Programmet er laget sommeren 2000, som et sommerprosjekt ved ITEA,
NTNU. Programmet er skrevet av John Magne Bredal, student ved NTNU,
Fakultet for Elektroteknikk og Telekommunikasjon, Linje for
Telematikk. 
<p>
I l�pet av h�sten er det kommet mer og mer forbedringer,
oppdateringer og bug-fikser, og jeg f�ler meg enn� ikke helt ferdig
med det. Vi har blant annet g�tt over til � bruke database i stedetfor
� la det v�re fil-basert og det er blitt mer og mer sentralt i NAV sitt
beskjedsendingsoppsett. De fleste programmene som vil sende ut mail
eller sms-meldinger p� bakgrunn av hendelser bruker n� TrapDetect.
</p>

<p><h3>Hva gj�r programmet:</h3></p>

<p> Programmet tar i mot traps vha. en snmptrap-daemon. Denne daemonen
lytter p� port 162, som er default snmptrap-port, og snapper opp
eventuelle pakker som er adressert til den. Deretter leser den
innholdet i pakken og sender informasjonen videre til programmet.
</p>

<p> Programmet behandler deretter informasjonen som kommer inn. Det
reagerer p� traps i henhold til ulike konfigurasjonsfiler, oppdaterer
filer og sender beskjeder via mail eller GSM. N�rmere detaljer vil jeg
ikke komme inn p� her, da det er uvesentlig for bruk av
web-siden. Interesserte kan henvende seg til meg p� adressen gitt
nederst p� siden.  </p>

<p> Hensikten med dette er � f� en oversikt over hva som skjer p�
nettverket, og samtidig v�re en varslingsstasjon for de som drifter
det. Ved � spesifisere hvilke traps og hvilke enheter som det skal
reageres p�, kan man luke ut det som er uviktig, og dermed slippe
un�dvendig "st�y". Hvis en enhet eller en link skulle g� ned, hvis det
er for mye last p� linjene, eller hvis enheten nettopp har m�ttet
restarte, s� vil man vite om det i l�pet av f� sekunder, og dermed
kunne reagere deretter.  </p>

<p><h3>Hva er "traps"?:</h3></p>

<p> En trap er en beskjed sendt via nettet fra en enhet vha. SNMP
(Simple Network Management Protocol).  Meningen med en trap er at den
skal inneholde statusinformasjon som enheten vil informere andre
enheter om. Derfor m� det v�re noe som for�rsaker at en trap sendes
ut. Dette konfigureres p� hver enhet, og kan v�re alt fra at en bruker
logger av enheten, til at enheten foretar en restart.  </p>

<p> En trap m� ha en mottaker for � ha mening. Eller, for � si det som
det egentlig er: en trap m� snappes opp av noen for at den skal v�re
informativ. Det er dette TrapDetect gj�r. Ved � bruke en nedlastet
snmptrap-daemon lytter det p� port 162, og snapper opp traps
der. Deretter ser programmet p� innholdet, og vurderer hva som skal
gj�res ut fra det.  </p>

<p> En stor del av informasjonen i en trap kommer fra OID'er (Object
IDentifier). En OID kan best sammenlignes med en unik tallrekke
adskilt av punktum som identifiserer informasjonen i
trap'en. F.eks. sier OID'en:<br> <b>.1.3.6.1.6.3.1.1.5.3</b><br> at
det er en linkDown-trap som er kommet inn. Hvis trap'en i tillegg
inneholder denne linjen:<br> <b>.1.3.6.1.2.1.2.2.1.1.18 18</b><br> s�
vet man at det er interFaceIndex 18 som har g�tt ned.  S� ved �
identifisere alle OID'ene i en trap, kan man finne ut hva som skjer og
handle deretter.  </p>

<p>
Mer utfyllende informasjon om SNMP, traps o.l. kan du finne blant
annet her:<br>
<a href="http://www.pantherdig.com/snmpfaq/">SNMP-FAQ</a><br>
<a href="http://www.cisco.com/univercd/cc/td/doc/cisintwk/ito_doc/snmp.htm">CISCO</a><br>
</p>

<p><h3>Oversikt over menyvalg:</h3></p>

<ul>

<a name="status"><li><b><u>STATUS</u></b></a>

   <p> Status viser oversikt over sykmeldinger som er kommet inn fra
   enhetene ved NTNU. De innleggene som er her, er ikke blitt
   friskmeldt, og sier noe om potensielle problemer ved enhetene som
   har sendt meldingene.  </p>

   <p> Innleggene gir informasjon om n�r trap'en kom inn, fra hvilken
   enhet (navn og ip-adresse), og eventuell mer info.  </p>

<a name="hendelsesregister"><li><b><u>HENDELSESREGISTER</u></b></a>

   <p> Hendelsesregistret er en liste over de siste hendelsene som er
   registrert. I registret er det oversikt over alle traps som er
   kommet inn i l�pet av det siste d�gnet, med start klokken 2400 hver
   natt/kveld. Registret viser oversikt over sykmeldinger, og
   eventuelle friskmeldinger. I tillegg vises oversikt over s�kalte
   tilstandsl�se traps, dvs. traps som ikke har friskmelding. Et
   eksempel p� slike er coldStart, en ren engangstrap som sier ifra om
   at enheten har foretatt en restart.  </p>

   <ul>
   <li><b><u>Dagens register</u></b>

   <p>Dagens register er en oversikt over hva som har skjedd fra
   klokken 24.00 og til n�. Friskmeldinger blir notert med dato under
   sykmeldingen. Ved s�k kan man velge mellom f�lgende alternativer: </p>

   <ul>

   <li><u>Friskmeldte</u>: Dette er sykmeldinger som har blitt
    friskmeldt vha. av en tilsvarende friskmeldingtrap. Dette kan skje
    med de fleste traps, men ikke med alle. Se kommentar om
    tilstandsl�se traps ovenfor.

    <li> <u>Sykmeldte</u>: Dette er generelle sykmeldinger som ikke er
    blitt friskmeldt. Dette kan ha to �rsaker: ingen friskmelding er
    kommet inn eller det er en tilstandsl�s trap som ikke kan f�
    friskmelding. NB!  Antall sykmeldinger i hendelsesregistret kan da
    bli st�rre enn antall sykmeldinger i status-oversikten. Dette er
    helt normalt.  <li><u>Begge</u>: Dette viser alle innlegg, b�de
    sykmeldinger og friskmeldinger.  </ul>

    <p> I tillegg kan man s�ke p� det man vil ved � taste inn en
    tekststreng i det hvite feltet, og man kan s�ke p� bestemte
    sykmeldinger ved � bruke drop-down-menyen til h�yre. Denne menyen
    oppdaterer seg selv automatisk fra TrapDetect.conf-fila, og vil
    dermed ha fullstendig oversikt over mulige sykmeldinger.  </p>

    <p> NB! Alle s�kefunksjoner kan brukes samtidig, s� hvis man vil
    ha en oversikt over alle friskmeldinger, med s�keord bredal, med
    sykmelding hystereseAlarmOn, s� er det fullt mulig.  </p>

    <li><b><u>Tidligere register</u></b>

    <p> Tidligere register gir deg mulighet til � se p� de tidligere
    hendelsesregistrene som er lagret. Man vil ha n�yaktig de samme
    mulighetene for s�k og oppslag som i Dagens register.  </p>

    <p> For � aksessere et tidligere register, skriv inn fra hvilken
    dato du vil ha oversikt over, og trykk Enter. Oversikten vil da
    komme opp. Datofeltet defaulter til g�rdagens dato, men det er
    fullt mulig � skrive inn en annen dato. Hvis register for denne
    dagen ikke finnes, vil du f� beskjed om det. Alle 6 tegn m�
    skrives, s� hvis du vil ha oversikt over 6 juli 2000, m� du skrive
    060700.  </p>

</ul>

<a name="logg"><li><b><u>LOGG</u></b></a>
	<p>
	 Loggen er for det meste ikke interessant for den vanlige bruker. Den
	 inneholder en r� og ubehandlet oversikt over alle traps som er kommet
	 inn, b�de traps som programmet reagerer p� og traps som programmet
	 overser. 
	</p>

	<p>
	 Det er imidlertid en del bruksomr�der n�r det gjelder loggen. For det
	 f�rste har man en oversikt over alt som har skjedd. I tillegg er det
	 mulig � tyde de OID'ene som er kommet inn, og finne ut om det er
	 interessant info eller ikke. Et siste bruksomr�de er debugging av
	 programmet, siden output til loggen er skrevet av programmet alt etter
	 hvilke aksjoner det har gjort med de ulike traps.
	</p>

<ul>
	 <li><b><u>Dagens logg</u></b>
	 
	  <p> Dagens logg er en oversikt over alt som har kommet inn
	   til programmet siden klokken 24.00 samme dag og frem til
	   n�. Den viser klokkeslett trap'en kom inn og uptime, navn
	   og ip-adresse p� enheten som sendte. I tillegg skrives alle
	   OID'er som er kommet inn med trap'en, og output fra
	   programmet.  </p>

	  <p> For � f� litt mer oversikt, kan man s�ke p�
	   tekststrenger i loggen. Skriv inn s�keord i det hvite
	   feltet og trykk Submit, evt. trykk Enter i tekstfeltet. Du
	   vil da f� oversikt over alle innlegg med s�keordet i. For �
	   f� oversikt over samtlige innlegg igjen, bare trykk p�
	   linken til Dagens logg, eller null ut tekstfeltet og trykk
	   Submit.  </p>

	 <li><b><u>Tidligere logg</u></b>

	 <p> Tidligere logg gir deg mulighet til � se p� de tidligere
	  loggene som er lagret. Man vil ha n�yaktig de samme
	  mulighetene for s�k som i Dagens logg.  </p>

	 <p> For � aksessere en tidligere logg, skriv inn fra hvilken
	  dato du vil ha loggen, og trykk Enter. Loggen vil da komme
	  opp. Datofeltet defaulter til g�rdagens dato, men det er
	  fullt mulig � skrive inn en annen dato. Hvis logg for denne
	  dagen ikke finnes, vil du f� beskjed om det. Alle 6 tegn m�
	  skrives, s� hvis du vil ha oversikt over 6 juli 2000, m� du
	  skrive 060700.  </p>

</ul>

<a name="statistikk"><li><b><u>STATISTIKK</u></b></a>
	
	<p> Statistikk inneholder en del oversikter som kan v�re b�de
	 nyttige og interessante. Statistikken best�r hovedsaklig av
	 to oversikter: en for antall traps mottatt pr. enhet, og en
	 for antall traps mottatt pr. OID.  </p>

<ul>	 <li><b><u>Generelt</u></b>

	 <p>Her vises en generell oversikt over alle traps som er
	 kommet inn, hvor mange av hver, fra hvilken enhet, hvor mange
	 totalt osv. Merk at dager tilbake sjelden overstiger
	 60. Dette fordi databasen dumpes hver m�ned, slik at det
	 f�rste innslaget i databasen alltid er fra tidlig i forrige
	 m�ned.</p>

	 <li><b><u>Traps pr. enhet</u></b> 
     
         <p> Viser en grafisk oversikt over antall traps som er
	 mottatt fra hver enhet i en tidsperiode som velges av bruker
	 Denne blir fort stor, da det er mange forskjellige enheter
	 som sender traps til programmet. Meningen med denne
	 fremstillingen er � f� god oversikt over hvilke enheter som
	 sender mest traps, og forholdet enhetene imellom.  </p>

	 <p> For hver s�yle/enhet er det mulig � klikke seg inn p� den
	 bestemte enheten og se detaljoversikt for hvilke traps den
	 har sendt ut. Data vil fremdeles v�re for det tidsrommet
	 brukeren valgte.</p>

	 <p> Videre er det ogs� mulig � klikke videre enda et steg for
	 � f� oversikt over de meldinger som er kommet inn. </p>

	<li><b><u>Traps inn</u></b>

	 <p> Viser en grafisk oversikt over antall traps som er
	 mottatt fra hver enhet i en tidsperiode som velges av bruker
	 Denne blir fort stor, da det er mange forskjellige enheter
	 som sender traps til programmet. Meningen med denne
	 fremstillingen er � f� god oversikt over hvilke OID'er som
	 forekommer oftest, og forholdet OID'ene imellom.  </p>

	 <p> Som for de andre statistikkene er det mulig � trykke seg
	 inn p� hver s�yle og se p� detaljoversikter. Her er det
	 oversikt over hvilke enheter som har sendt ut denne typen OID
	 i l�pet av det valgte tidsrommet. </p>

	 <p> Videre er det ogs� mulig � klikke videre enda et steg for
	 � f� oversikt over de meldinger som er kommet inn. Se MERKNAD
	 ovenfor</p>

</ul>

<a name="diverse"><li><b><u>DIVERSE</u></b></a>
  <p>
    Herunder kommer det som ikke lar seg klassifisere under andre overskrifter.
  </p>
<ul>

   <li><b><u>Redigering av innlegg</b></u>

   <p>
    For � komme til denne linken m� du ha administreringsadgang
    til sidene. Du vil bli spurt om brukernavn og passord for � komme
    inn. 
   </p>

   <p>
    Her kan du redigere innlegg. Du f�r en oversikt over n�v�rende
    status, og valg mellom � slette eller friskmelde innlegg. For � velge
    hvilke innlegg du vil redigere trykker du p� knappen ved siden av
    innlegget. N�r du har valgt alle innlegg du vil gj�re noe med,
    trykker du <i>Slett</i> eller <i>Friskmeld</i>, skriver inn navnet ditt for
    registrering og trykker Submit. 
   </p>

   <p>NB! Navnet ditt vil ikke ha noen
    betydning ved sletting av innlegg, bare ved friskmelding. Det vil da st� ved
    siden av friskmeldingen hvem som har friskmeldt innlegget.
   </p>

</ul>
</ul>

<p><h3>Referanser/Copyright:</h3></p>
<ul>
	<li>Dette systemet er gjort mulig vha:
	<ul>
		<li><a href="http://www.perl.com">PERL</a>
		<li><a href="http://ucd-snmp.ucdavis.edu/">UCD-SNMP -
		programpakke</a>
		<li><a href="http://www.php.net">PHP</a>
		<li><a href="http://www.linux.org">Linux</a>
		<li><a
		href="http://www.gnu.org/software/emacs/emacs.html">EMACS</a> - The only option
		<li>Kaffe - stoooore mengder
		<li>Folk og r�vere p� ITEA/Teknostallen som har kommet med gode
		r�d og forslag.
	</ul>
</ul>

<p><h3>Sp�rsm�l:</h3></p>

<p>Eventuelle sp�rsm�l/klager/meninger kan rettes til meg
personlig:</p>
<p>
John Magne Bredal<br>
Tlf: 91 56 52 66<br>
Email: bredal@stud.ntnu.no<br>
</p>
<p>
Mest sannsynlig vil jeg ikke svare med mindre mailen kommer fra
ITEA-ansatte... :)
</p>

<?php bunntabell() ?>



