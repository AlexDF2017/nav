/*******************
*
* $Id: NavUtils.java,v 1.10 2003/06/25 15:09:25 kristian Exp $
* This file is part of the NAV project.
* Topologi- og vlanavleder
*
* Copyright (c) 2002 by NTNU, ITEA nettgruppen
* Authors: Kristian Eide <kreide@online.no>
*
*******************/

import java.io.*;
import java.util.*;
import java.net.*;
import java.text.*;

import java.sql.*;

import no.ntnu.nav.ConfigParser.*;
import no.ntnu.nav.Database.*;
import no.ntnu.nav.event.*;
import no.ntnu.nav.Path;
import no.ntnu.nav.util.*;


class networkDiscovery
{
	public static final String dbConfigFile = (Path.sysconfdir + "/db.conf").replace('/', File.separatorChar);;
	public static final String scriptName = "networkDiscovery";

	private static String debugParam;

	public networkDiscovery() {

	}

	// Main metoden
	public static void main(String[] args) throws IOException
	{
		networkDiscovery nu = new networkDiscovery();

		if (args.length < 1)
		{
			nu.outl("Arguments: [configFile] <options>\n");
			nu.outl("Where options include:\n");
			nu.outl("   topology\tDiscover the network topology using data collected via SNMP.");
			nu.outl("   vlan\tDiscover which VLANs are running on each network link");
			nu.outl("   debug\tTurn on debugging output.");
			return;
		}

		int beginOptions = 0;
		String configFile = args[0];
		ConfigParser cp, dbCp;
		/*
		if (!configFile.startsWith("-")) {
			beginOptions = 1;
			try {
				cp = new ConfigParser(configFile);
			} catch (IOException e) {
				nu.outl("Error, could not read config file: " + configFile);
				return;
			}
		}
		*/
		try {
			dbCp = new ConfigParser(dbConfigFile);
		} catch (IOException e) {
			nu.outl("Error, could not read database config file: " + dbConfigFile);
			return;
		}
		if (!Database.openConnection(dbCp.get("dbhost"), dbCp.get("dbport"), dbCp.get("db_nav"), dbCp.get("script_"+scriptName), dbCp.get("userpw_"+dbCp.get("script_"+scriptName)))) {
			nu.outl("Error, could not connect to database!");
			return;
		}

		Set argSet = new HashSet();
		for (int i=beginOptions; i < args.length; i++) argSet.add(args[i]);

		if (argSet.contains("debug")) debugParam = "yes";

		try {
			String title;
			if (argSet.contains("topology")) title = "Network discovery report";
			else if (argSet.contains("vlan")) title = "Vlan discovery report";
			else title = "Argument is not valid";

			nu.outl("<html>");
			nu.outl("<head><title>"+title+"</title></head>");
			nu.outl("<body>");

			if (argSet.contains("topology")) nu.avledTopologi();
			else if (argSet.contains("vlan")) nu.avledVlan();
			else {
				nu.outl("Argument is not valid, start without arguments for help.");
			}

			nu.outl("</body>");
			nu.outl("</html>");

		} catch (SQLException e) {
			nu.errl("SQLException: " + e.getMessage());
			e.printStackTrace(System.err);
		}

	}

	/*
	private String mpToIfindex(String modul, String port)
	{
		int m,p;

		try {
			if (modul.startsWith("Fa")) m = Integer.parseInt(modul.substring(2, modul.length()));
			else if (modul.startsWith("Gi")) m = 100+Integer.parseInt(modul.substring(2, modul.length()));
			else m = Integer.parseInt(modul);

			p = Integer.parseInt(port);
		} catch (NumberFormatException e) {
			outl("ERROR, NumberFormatExeption: Modul: " + modul + " Port: " + port);
			return null;
		}
		return String.valueOf(m)+String.valueOf(p);
	}
	*/

	public void avledTopologi() throws SQLException
	{
		boolean DEBUG_OUT = false;
		//String debugParam = com.getp("debug");
		if (debugParam != null && debugParam.equals("yes")) DEBUG_OUT = true;
		Boks.DEBUG_OUT = DEBUG_OUT;

		if (DEBUG_OUT) outl("Begin<br>");

		// Vis dato
		{
			java.util.Date currentTime = new GregorianCalendar().getTime();
			outl("Generated on: <b>" + currentTime + "</b><br>");
		}

		Map boksNavn = new HashMap();
		Map boksType = new HashMap();
		Map boksKat = new HashMap();
		ResultSet rs = Database.query("SELECT netboxid,sysName,typename,catid FROM netbox LEFT JOIN type USING(typeid)");
		while (rs.next()) {
			String sysname = rs.getString("sysName"); // M� v�re med da sysname kan v�re null !!
			boksNavn.put(new Integer(rs.getInt("netboxid")), (sysname==null?"&lt;null&gt;":sysname) );
			boksType.put(new Integer(rs.getInt("netboxid")), rs.getString("typename"));
			boksKat.put(new Integer(rs.getInt("netboxid")), rs.getString("catid"));
		}
		Boks.boksNavn = boksNavn;
		Boks.boksType = boksType;

		Set gwUplink = new HashSet();
		rs = Database.query("SELECT DISTINCT ON (to_netboxid) to_netboxid FROM gwport WHERE to_netboxid IS NOT NULL");
		while (rs.next()) {
			gwUplink.add(rs.getString("to_netboxid"));
		}

		// Endret for � f� med GSW
		//rs = Database.query("SELECT swp_netbox.netboxid,catid,swp_netbox.module,port,swp_netbox.to_netboxid,swp_netbox.to_module,swp_netbox.to_port,module.netboxid AS gwnetboxid FROM swp_netbox JOIN netbox USING(netboxid) JOIN prefix USING(prefixid) LEFT JOIN gwport ON (rootgwid=gwportid) LEFT JOIN module USING (moduleid) WHERE gwportid IS NOT NULL OR catid='GSW' ORDER BY netboxid,module,port");
		//rs = Database.query("SELECT swp_netbox.netboxid,catid,swp_netbox.ifindex,swp_netbox.to_netboxid,swport.ifindex AS to_ifindex,module.netboxid AS gwnetboxid FROM swp_netbox JOIN netbox USING(netboxid) JOIN prefix USING(prefixid) LEFT JOIN gwportprefix USING(prefixid) LEFT JOIN gwport USING(gwportid) LEFT JOIN module USING (moduleid) LEFT JOIN swport ON (swp_netbox.to_swportid=swport.swportid) WHERE gwportid IS NOT NULL OR catid='GSW' ORDER BY netboxid,swp_netbox.ifindex");

		rs = Database.query("SELECT swp_netbox.netboxid,catid,swp_netbox.ifindex,swp_netbox.to_netboxid,swport.ifindex AS to_ifindex,module.netboxid AS gwnetboxid FROM swp_netbox JOIN netbox USING(netboxid) LEFT JOIN gwportprefix ON (netbox.prefixid = gwportprefix.prefixid AND (hsrp='t' OR gwip::text IN (SELECT MIN(gwip::text) FROM gwportprefix GROUP BY prefixid HAVING COUNT(DISTINCT hsrp) = 1))) LEFT JOIN gwport USING(gwportid) LEFT JOIN module USING (moduleid) LEFT JOIN swport ON (swp_netbox.to_swportid=swport.swportid) WHERE gwportid IS NOT NULL OR catid='GSW' ORDER BY netboxid,swp_netbox.ifindex");




		Map bokser = new HashMap();
		List boksList = new ArrayList();
		List l = null;
		Set boksidSet = new HashSet();
		Set boksbakidSet = new HashSet();

		//int previd = rs.getInt("boksid");
		int previd = 0;
		while (rs.next()) {
			int boksid = rs.getInt("netboxid");
			if (boksid != previd) {
				// Ny boks
				l = new ArrayList();
				boolean isSW = (rs.getString("catid").equals("SW") ||
												rs.getString("catid").equals("GW") ||
												rs.getString("catid").equals("GSW"));
				Boks b = new Boks(boksid, rs.getInt("gwnetboxid"), l, bokser, isSW, !gwUplink.contains(String.valueOf(boksid)) );
				boksList.add(b);
				previd = boksid;
			}
			String[] s = {
				rs.getString("ifindex"),
				//rs.getString("port"),
				rs.getString("to_netboxid"),
				rs.getString("to_ifindex")
				//rs.getString("to_port")
			};
			l.add(s);

			boksidSet.add(new Integer(boksid));
			boksbakidSet.add(new Integer(rs.getInt("to_netboxid")));
		}

		int maxBehindMp=0;
		for (int i=0; i < boksList.size(); i++) {
			Boks b = (Boks)boksList.get(i);
			bokser.put(b.getBoksidI(), b);
			b.init();
			if (b.maxBehindMp() > maxBehindMp) maxBehindMp = b.maxBehindMp();
		}

		// Legg til alle enheter vi bare har funnet i boksbak
		boksbakidSet.removeAll(boksidSet);
		Iterator iter = boksbakidSet.iterator();
		while (iter.hasNext()) {
			Integer boksbakid = (Integer)iter.next();

			String kat = (String)boksKat.get(boksbakid);
			if (kat == null) {
				errl("Error! kat not found for boksid: " + boksbakid);
			}
			boolean isSW = (kat.equals("SW") ||
							kat.equals("GW") ||
							kat.equals("GSW"));

			Boks b = new Boks(boksbakid.intValue(), 0, null, bokser, isSW, true);
			if (!bokser.containsKey(b.getBoksidI())) boksList.add(b);
			bokser.put(b.getBoksidI(), b);
			if (DEBUG_OUT) outl("Adding boksbak("+b.getBoksid()+"): <b>"+b.getName()+"</b><br>");
		}

		if (DEBUG_OUT) outl("Begin processing, maxBehindMp: <b>"+maxBehindMp+"</b><br>");

		for (int level=1; level <= maxBehindMp; level++) {
			boolean done = true;
			for (int i=0; i < boksList.size(); i++) {
				Boks b = (Boks)boksList.get(i);
				if (b.proc_mp(level)) done = false;
			}
			for (int i=0; i < boksList.size(); i++) {
				Boks b = (Boks)boksList.get(i);
				b.removeFromMp();
			}
			if (!done) {
				if (DEBUG_OUT) outl("Level: <b>"+level+"</b>, state changed.<br>");
			}
		}
		// Til slutt sjekker vi uplink-portene, dette vil normalt kun gjelde uplink mot -gw
		for (int i=0; i < boksList.size(); i++) {
			Boks b = (Boks)boksList.get(i);
			b.proc_mp(Boks.PROC_UPLINK_LEVEL);
		}

		if (DEBUG_OUT) outl("<b>BEGIN REPORT</b><br>");
		for (int i=0; i < boksList.size(); i++) {
			Boks b = (Boks)boksList.get(i);
			if (DEBUG_OUT) b.report();
			b.guess();
		}
		HashMap boksMp = new HashMap();
		for (int i=0; i < boksList.size(); i++) {
			Boks b = (Boks)boksList.get(i);
			b.addToMp(boksMp);
		}
		if (DEBUG_OUT) outl("Report done.<br>");

		/*
		// Vi m� vite hvilke bokser som har trunker ut fra seg, dvs. det kj�rer flere vlan
		HashSet boksWithTrunk = new HashSet();
		rs = Database.query("SELECT DISTINCT netboxid FROM swport JOIN module USING(moduleid) WHERE trunk='t'");
		while (rs.next()) boksWithTrunk.add(rs.getString("netboxid"));
		*/

		/*
		// Vi trenger en oversikt over hvilket vlan de forskjellige boksene er p�
		HashMap boksVlan = new HashMap();
		rs = Database.query("SELECT netboxid,vlan FROM netbox JOIN prefix USING (prefixid) JOIN vlan USING(vlanid) WHERE vlanid IS NOT NULL");
		while (rs.next()) {
			boksVlan.put(rs.getString("netboxid"), rs.getString("vlan"));
		}
		*/

		// N� g�r vi gjennom alle portene vi har funnet boksbak for, og oppdaterer tabellen med dette
		int newcnt=0,updcnt=0,resetcnt=0;
		ArrayList swport = new ArrayList();
		HashMap swrecMap = new HashMap();
		Map swrecSwportidMap = new HashMap();
		rs = Database.query("SELECT swportid,netboxid,link,speed,duplex,ifindex,portname,to_netboxid,trunk,hexstring FROM swport JOIN module USING(moduleid) LEFT JOIN swportallowedvlan USING (swportid) ORDER BY netboxid,ifindex");
		ResultSetMetaData rsmd = rs.getMetaData();
		while (rs.next()) {
			HashMap hm = getHashFromResultSet(rs, rsmd);
			String link = rs.getString("link");
			if (link == null || link.toLowerCase().equals("y")) swport.add(hm);
			String key = rs.getString("netboxid")+":"+rs.getString("ifindex");
			swrecMap.put(key, hm);
			swrecSwportidMap.put(rs.getString("swportid"), hm);
		}

		if (DEBUG_OUT) outl("boksMp listing....<br>");
		iter = boksMp.entrySet().iterator();
		while (iter.hasNext()) {
			Map.Entry me = (Map.Entry)iter.next();
			String key = (String)me.getKey();
			//Integer boksbak = (Integer)me.getValue();
			BoksMpBak bmp = (BoksMpBak)me.getValue();

			StringTokenizer st = new StringTokenizer(key, ":");
			String boksid;
			String ifindex;
			try {
				boksid = st.nextToken();
				ifindex = st.nextToken();
			} catch (Exception e) {
				errl("Exception: " + e.getMessage() + " Key: " + key + " bmp: " + bmp);
				e.printStackTrace(System.err);
				return;
			}

			//outl(boksNavn.get(new Integer(boksid)) + " Modul: " + modul + " Port: " + port + " Link: " + boksNavn.get(boksbak) + "<br>");

			if (swrecMap.containsKey(key)) {
				// Record eksisterer fra f�r, sjekk om oppdatering er n�dvendig
				HashMap swrec = (HashMap)swrecMap.get(key);
				//swrecMap.remove(key);
				swrec.put("deleted", null);

				String link = (String)swrec.get("link");
				if (link != null) link = link.toLowerCase();
				if ("n".equals(link)) continue; // Ignore non-up links

				String idbak = (String)swrec.get("to_netboxid");
				if (idbak == null || idbak != null && Integer.parseInt(idbak) != bmp.boksbak.intValue()) {
					// Oppdatering n�dvendig
					updcnt++;
					// swport
					{
						String[] updateFields = {
							"to_netboxid", bmp.boksbak.toString()
						};
						String[] condFields = {
							"swportid", (String)swrec.get("swportid")
						};
						Database.update("swport", updateFields, condFields);
					}

					String vlan = "non-s";

					/*
					if (swrec.get("static").equals("t")) {
						if (swrec.get("trunk").equals("t")) {
							// Vi har en static trunk, pr�v � finn record for andre veien
							Boks b = (Boks)bokser.get(boksbak);
							Mp uplinkMp = b.getMpTo(new Integer(boksid));
							if (uplinkMp != null) {
								// Port funnet, men eksisterer denne porten i tabellen fra f�r?
								String keyBak = boksbak+":"+uplinkMp;
								if (swrecMap.containsKey(keyBak)) {
									// Eksisterer fra f�r, sjekk om det er en trunk
									HashMap swrecBak = (HashMap)swrecMap.get(keyBak);
									if ("t".equals(swrecBak.get("trunk"))) {
										// Trunk, sjekk om vi m� oppdatere swportallowedvlan
										String allowedVlan = (String)swrec.get("hexstring");
										String allowedVlanBak = (String)swrecBak.get("hexstring");
										if (!allowedVlan.equals(allowedVlanBak)) {
											// Oppdatering n�dvendig
											String[] updateFields = {
												"hexstring", allowedVlan
											};
											String[] condFields = {
												"swportid", (String)swrec.get("swportid")
											};
											Database.update("swportallowedvlan", updateFields, condFields);
											if (DEBUG_OUT) outl("Updated swportallowedvlan, swportid: " + condFields[0] + " hexstring: " + allowedVlan + "<br>");
										}
									}
								}
							}
							vlan = "trunk";

						} else {
							// swportvlan
							if (boksWithTrunk.contains(boksbak.toString())) {
								// Boksen i andre enden har trunk, da m� vi bruke v�rt eget vlan
								vlan = (String)boksVlan.get(boksid);
							} else {
								vlan = (String)boksVlan.get(boksbak.toString());
							}
							if (vlan != null) {
								String[] updateFields = {
									"vlan", vlan,
									"retning", "s"
								};
								String[] condFields = {
									"swportid", (String)swrec.get("swportid")
								};
								Database.update("swportvlan", updateFields, condFields);
							}
						}
					}
					*/

					swrec.put("to_netboxid", bmp.boksbak.toString());
					swrec.put("change", "Updated ("+vlan+")");
				}

				// S� m� vi sjekke om swportbak skal oppdateres
				boolean swportbakOK = false;
				if (bmp.toIfindex != null) {
					// OK, sl� opp i swportMap for � finne riktig swportid
					Map swrecBak = (Map)swrecMap.get(bmp.hashKey());
					if (swrecBak != null) {
						swportbakOK = true;
						String new_swportbak = (String)swrecBak.get("swportid");
						String cur_swportbak = (String)swrec.get("to_swportid");

						if (cur_swportbak == null || !cur_swportbak.equals(new_swportbak)) {
							String[] updateFields = {
								"to_swportid", new_swportbak
							};
							String[] condFields = {
								"swportid", (String)swrec.get("swportid")
							};
							Database.update("swport", updateFields, condFields);
						}
					} else {
						// Feilsitasjon!
						outl("<font color=\"red\">ERROR:</font> Could not find record in swport,  boks("+bmp.boksbak+"): <b>" + boksNavn.get(bmp.boksbak) + "</b> Ifindex: <b>" + bmp.toIfindex + "</b> boksbak: <b>" + boksNavn.get(new Integer(boksid)) + "</b> ("+bmp.hashKey()+")<br>");
					}
				}

				/*
				if (!swportbakOK) {
					outl("Removing deleted for swportid " + swrec.get("swportid") + "<br>");
					swrec.remove("deleted");
				}
				*/

				// S� m� vi sjekke om vi har en trunk der vi mangler allowedvlan
				if ("t".equals(swrec.get("trunk")) && (swrec.get("hexstring") == null || swrec.get("hexstring").equals("")) ) {
					// Vi har en trunk som er static eller mangler hexstring, da tar vi rett og slett bare hexstringen fra andre siden og setter inn

					Boks b = (Boks)bokser.get(bmp.boksbak);
					//Mp mpBak = b.getMpTo(Integer.parseInt(boksid), modul, port);
					String toIfindex = b.getIfindexTo(Integer.parseInt(boksid), ifindex);
					if (toIfindex != null) {
						// Port p� andre siden funnet, men eksisterer denne porten i tabellen?
						String keyBak = bmp.boksbak+":"+toIfindex;
						if (swrecMap.containsKey(keyBak)) {
							// Eksisterer, sjekk om det er en trunk
							HashMap swrecBak = (HashMap)swrecMap.get(keyBak);
							if ("t".equals(swrecBak.get("trunk"))) {
								// Trunk, sjekk om vi m� oppdatere swportallowedvlan
								String allowedVlan = (String)swrec.get("hexstring");
								String allowedVlanBak = (String)swrecBak.get("hexstring");
								if (allowedVlan == null || allowedVlan.length() == 0) {
									if (allowedVlanBak == null || allowedVlanBak.length() == 0) {
										// Feilsituasjon! N� er vi i virkelig tr�bbel, da det er static trunk p� begge sider...
										outl("<font color=\"red\">ERROR:</font> Link is trunk with no swportallowedvlan on either side! boks: " + boksNavn.get(new Integer(boksid)) + " Ifindex: " + ifindex+ " boksBak: " + boksNavn.get(bmp.boksbak) + " ToIfindex: " + swrecBak.get("ifindex") + "<br>");

									} else {
										// N� m� vi sette inn en ny record i swportallowedvlan
										String[] fields = {
											"swportid", (String)swrec.get("swportid"),
											"hexstring", allowedVlanBak
										};
										if (DEBUG_OUT) outl("Inserting new record in swportallowedvlan, swportid: " + swrec.get("swportid") + " new hexstring: " + allowedVlanBak + "<br>");
										boolean update = false;
										try {
											Database.insert("swportallowedvlan", fields);
										} catch (SQLException e) {
											// Wops, pr�v � oppdatere i steden
											update = true;
										}
										if (update) try {
											outl("<font color=\"red\">ERROR:</font> swportallowedvlan seems to already have an empty record! Trying to update instead...<br>");
											Database.update("UPDATE swportallowedvlan SET hexstring='"+allowedVlanBak+"' WHERE swportid='"+swrec.get("swportid")+"'");
										} catch (SQLException e) {
											outl("<font color=\"red\">ERROR:</font> Cannot update swportallowedvlan, SQLException: " + e.getMessage() + "<br>");
										}
									}

								} else if (!allowedVlan.equals(allowedVlanBak)) {
									// Oppdatering n�dvendig
									String[] updateFields = {
										"hexstring", allowedVlanBak
									};
									String[] condFields = {
										"swportid", (String)swrec.get("swportid")
									};
									Database.update("swportallowedvlan", updateFields, condFields);
									if (DEBUG_OUT) outl("Updated swportallowedvlan, swportid: " + condFields[0] + " old hexstring: " + allowedVlan + " new hexstring: " + allowedVlanBak + "<br>");
								}
							} else {
								// Feilsituasjon, trunk<->non-trunk!
								outl("<font color=\"red\">ERROR:</font> Link is trunk / non-trunk: boks: " + boksNavn.get(new Integer(boksid)) + " Ifindex: " + ifindex + " boksBak: " + boksNavn.get(bmp.boksbak) + " ToIfindex: " + swrecBak.get("ifindex") + "<br>");
							}
						}
					}
				}


			} else {
				// Dette er n� en feilsituasjon som ikke b�r skje! :-)
				outl("<font color=\"red\">ERROR:</font> Could not find record for other side of link! boks("+boksid+"): <b>" + boksNavn.get(new Integer(boksid)) + "</b> Ifindex: <b>" + ifindex + "</b> boksBak: <b>" + boksNavn.get(bmp.boksbak) + "</b><br>");

			}

			/*
			else {
				// Record eksister ikke, og m� derfor settes inn

				// F�rst m� vi sjekke om andre siden er en trunk
				String vlan;
				String trunk = "f";
				String allowedVlan = null;
				{
					Boks b = (Boks)bokser.get(boksbak);
					Mp uplinkMp = b.getMpTo(new Integer(boksid));
					if (uplinkMp != null) {
						// Port funnet, men eksisterer denne porten i tabellen fra f�r?
						String keyBak = boksbak+":"+uplinkMp;
						if (swrecMap.containsKey(keyBak)) {
							// Eksisterer fra f�r, sjekk om det er en trunk
							HashMap swrecBak = (HashMap)swrecMap.get(keyBak);
							if ("t".equals(swrecBak.get("trunk"))) {
								// Trunk, da m� vi ogs� sette inn i swportallowedvlan
								trunk = "t";
								allowedVlan = (String)swrecBak.get("hexstring");
							}
						}
					}

					if (trunk.equals("t")) {
						vlan = "t";
					} else if (boksWithTrunk.contains(boksbak.toString())) {
						// Boksen i andre enden har trunk, da m� vi bruke v�rt eget vlan
						vlan = (String)boksVlan.get(boksid);
					} else {
						vlan = (String)boksVlan.get(boksbak.toString());
					}

					if (vlan != null) {
						// Vi setter kun inn i swport hvis vi vet vlan eller det er en trunk det er snakk om
						// swport
						String ifind = mpToIfindex(modul, port);
						if (ifind != null) {
							String[] insertFields = {
								"boksid", boksid,
								"ifindex", ifind,
								"status", "up",
								"trunk", trunk,
								"static", "t",
								"modul", modul,
								"port", port,
								"boksbak", boksbak.toString()
							};
							if (!Database.insert("swport", insertFields)) {
								outl("<font color=\"red\">Error with insert, boksid=" + boksid + " trunk="+trunk+" ifindex=" + insertFields[1] + " modul="+modul+" port="+port+" boksbak="+boksbak+"</font><br>");
							} else {
								if (DEBUG_OUT) outl("Inserted row, boksid=" + boksid + " trunk="+trunk+" ifindex="+insertFields[1]+" modul="+modul+" port="+port+" boksbak="+boksbak+"<br>");
								//Database.commit();
								newcnt++;
							}
						}

					}


				}

				// Hvis trunk setter vi inn i swportallowedvlan, ellers rett inn i swportvlan
				if (trunk.equals("t")) {
					// swportallowedvlan
					String sql = "INSERT INTO swportallowedvlan (swportid,hexstring) VALUES ("+
								 "(SELECT swportid FROM swport WHERE boksid='"+boksid+"' AND modul='"+modul+"' AND port='"+port+"' AND boksbak='"+boksbak+"'),"+
								 "'"+allowedVlan+"')";
					Database.update(sql);
					if (DEBUG_OUT) outl("swportallowedvlan: "+sql+"<br>");

				} else
				if (vlan != null) {
				// swportvlan
				// Hvilket vlan g�r over linken? Vi henter vlanet boksbak er p�

					// Siden vi ikke vet fremmedn�kkelen m� vi bruke sub-select her
					String sql = "INSERT INTO swportvlan (swportid,vlan,retning) VALUES ("+
								 "(SELECT swportid FROM swport WHERE boksid='"+boksid+"' AND modul='"+modul+"' AND port='"+port+"' AND boksbak='"+boksbak+"'),"+
								 "'"+vlan+"',"+
								 "'s')";
					Database.update(sql);
					if (DEBUG_OUT) outl("swportvlan: "+sql+"<br>");
				}


				// Lag swrec
				HashMap swrec = new HashMap();
				swrec.put("swportid", "N/A");
				swrec.put("boksid", boksid);
				swrec.put("status", "up");
				swrec.put("speed", null);
				swrec.put("duplex", null);
				swrec.put("modul", modul);
				swrec.put("port", port);
				swrec.put("portnavn", null);
				swrec.put("boksbak", boksbak.toString());
				swrec.put("static", "t");
				if (vlan != null) {
					swrec.put("change", "Inserted ("+vlan+")");
				} else {
					swrec.put("change", "Error, vlan is null");
				}

				swport.add(swrec);
				//swrecMap.put(key, swrec);
			}
			*/

		}
		if (DEBUG_OUT) outl("boksMp listing done.<br>");

		iter = swrecMap.entrySet().iterator();
		while (iter.hasNext()) {
			Map.Entry me = (Map.Entry)iter.next();
			String key = (String)me.getKey();
			HashMap swrec = (HashMap)me.getValue();

			String swportid = (String)swrec.get("swportid");
			String boksbak = (String)swrec.get("to_netboxid");
			String swportbak = (String)swrec.get("to_swportid");

			if (swportbak != null && swportbak.length() > 0) {
				boolean reset = false;
				if (boksbak == null || boksbak.length() == 0) {
					reset = true;
				} else {
					Map swrecBak = (Map)swrecSwportidMap.get(swportbak);
					if (swrecBak == null || !boksbak.equals(swrecBak.get("netboxid"))) {
						reset = true;
					}
				}

				if (reset) {
					resetcnt++;
					// Sett felter til null
					String[] updateFields = {
						"to_swportid", "null"
					};
					String[] condFields = {
						"swportid", swportid
					};
					Database.update("swport", updateFields, condFields);
					if (DEBUG_OUT) outl("Want to reset swportbak(2) for swportid: " + swportid + "<br>");
					swportbak = null;
				}
			}

			if (swrec.containsKey("deleted")) continue;


			if (boksbak != null && boksbak.length() > 0) {
				// Sett til null
				resetcnt++;
				String[] updateFields = {
					"to_netboxid", "null",
					"to_swportid", "null"
				};
				String[] condFields = {
					"swportid", swportid
				};
				Database.update("swport", updateFields, condFields);
				if (DEBUG_OUT) outl("Want to reset boksbak for swportid: " + swportid + "<br>");
			}
			else if (swportbak != null && swportbak.length() > 0) {
				// Sett felter til null
				resetcnt++;
				String[] updateFields = {
					"to_swportid", "null"
				};
				String[] condFields = {
					"swportid", swportid
				};
				Database.update("swport", updateFields, condFields);
				if (DEBUG_OUT) outl("Want to reset swportbak for swportid: " + swportid + "<br>");
			}

		}

		/*
		iter = swrecMap.entrySet().iterator();
		while (iter.hasNext()) {
			Map.Entry me = (Map.Entry)iter.next();
			String key = (String)me.getKey();
			HashMap swrec = (HashMap)me.getValue();

			//if (!swrec.get("static").equals("t")) continue;
			if (swrec.containsKey("deleted")) continue;

			remcnt++;

			StringTokenizer st = new StringTokenizer(key, ":");
			String boksid = st.nextToken();
			String modul = st.nextToken();
			String port = st.nextToken();

			String swportid = (String)swrec.get("swportid");

			// boksbak_s kan egentlig ikke v�re null, men for sikkerhets skyld
			String boksbak_s = (String)swrec.get("boksbak");
			Integer boksbak = (boksbak_s == null) ? new Integer(0-1) : new Integer((String)swrec.get("boksbak"));

			//Database.update("DELETE FROM swport WHERE swportid='"+swportid+"'");
			if (DEBUG_OUT) outl("[DELETED] swportid: <b>"+swportid+"</b> sysName: <b>" + boksNavn.get(new Integer(boksid)) + "</b> Modul: <b>" + modul + "</b> Port: <b>" + port + "</b> Link: <b>" + boksNavn.get(boksbak) + "</b><br>");
		}
		*/

		outl("<table>");
		outl("  <tr>");
		outl("    <td><b>swpid</b></td>");
		outl("    <td><b>boksid</b></td>");
		outl("    <td><b>sysName</b></td>");
		outl("    <td><b>typeId</b></td>");
		outl("    <td><b>Speed</b></td>");
		outl("    <td><b>Duplex</b></td>");
		outl("    <td><b>Ifindex</b></td>");
		outl("    <td><b>Portnavn</b></td>");
		outl("    <td><b>Boksbak</b></td>");
		outl("    <td><b>Change (vlan)</b></td>");
		outl("  </tr>");

		int attCnt=0;
		for (int i=0; i < swport.size(); i++) {
			HashMap swrec = (HashMap)swport.get(i);
			String boksid = (String)swrec.get("netboxid");
			String ifindex = (String)swrec.get("ifindex");
			String portnavn = (String)swrec.get("portname");
			//boolean isStatic = swrec.get("static").equals("t");
			String change = (String)swrec.get("change");

			if (portnavn == null) portnavn = "";

			String boksbak = "";
			//Integer idbak = (Integer)boksMp.get(boksid+":"+modul+":"+port);
			BoksMpBak bmp = (BoksMpBak)boksMp.get(boksid+":"+ifindex);
			Integer idbak = (bmp != null) ? bmp.boksbak : null;
			if (idbak != null) boksbak = (String)boksNavn.get(idbak);
			if (boksbak == null) {
				outl("ERROR! boksbak is null for idbak: " + idbak + "<br>");
				continue;
			}

			String color = "gray";
			if (change != null && change.startsWith("Error")) {
				color = "red";
			} else
			if (portnavn.length() == 0 && boksbak.length()>0) {
				color = "blue";
			} else
			if (portnavn.length() > 0 && boksbak.length()==0) {
				if (portnavn.indexOf("-h") != -1 || portnavn.indexOf("-sw") != -1 || portnavn.indexOf("-gw") != -1) {
					color = "purple";
				}
			} else
			if (portnavn.length() > 0 && boksbak.length()>0 && portnavn.endsWith(boksbak) ) {
				color = "green";
			} else
			if (portnavn.length() > 0 && boksbak.length()>0 && !portnavn.endsWith(boksbak) ) {
				color = "red";
			}

			if (!color.equals("purple") && !color.equals("red")) continue;
			if (portnavn.length() > 2 && portnavn.charAt(0) == 'n' && portnavn.charAt(2) == ':') continue;

			attCnt++;
			String color1 = "<font color="+color+">";
			String color2 = "</font>";

			outl("<tr>");
			//outl("<td align=right>"+color1+ swrec.get("swportid") + color2+"</td>");
			outl("<td align=right><a href=\"#" + swrec.get("swportid") + "\">" + swrec.get("swportid") + "</a></td>");
			outl("<td align=right>"+color1+ swrec.get("netboxid") + color2+"</td>");
			outl("<td>"+color1+ boksNavn.get(new Integer((String)swrec.get("netboxid"))) + color2+"</td>");
			outl("<td>"+color1+ boksType.get(new Integer((String)swrec.get("netboxid"))) + color2+"</td>");
			outl("<td align=right>"+color1+ swrec.get("speed") + color2+"</td>");
			outl("<td align=right>"+color1+ swrec.get("duplex") + color2+"</td>");
			outl("<td align=right>"+color1+ swrec.get("ifindex") + color2+"</td>");
			outl("<td>"+color1+ portnavn + color2+"</td>");
			outl("<td>"+color1+ boksbak + color2+"</td>");

			if (change != null) outl("<td><b>"+change+"</b></td>");

			outl("</tr>");
		}
		outl("</table>");
		outl("Found <b>" + attCnt + "</b> rows in need of attention.<br>");

		outl("<h2>swport:</h2>");
		outl("<table>");
		outl("  <tr>");
		outl("    <td><b>swpid</b></td>");
		outl("    <td><b>boksid</b></td>");
		outl("    <td><b>sysName</b></td>");
		outl("    <td><b>Speed</b></td>");
		outl("    <td><b>Duplex</b></td>");
		outl("    <td><b>Ifindex</b></td>");
		outl("    <td><b>Portnavn</b></td>");
		outl("    <td><b>Boksbak</b></td>");
		outl("    <td><b>Change (vlan)</b></td>");
		outl("  </tr>");

		for (int i=0; i < swport.size(); i++) {
			HashMap swrec = (HashMap)swport.get(i);
			String boksid = (String)swrec.get("netboxid");
			String ifindex = (String)swrec.get("ifindex");
			String portnavn = (String)swrec.get("portname");
			//boolean isStatic = swrec.get("static").equals("t");
			String change = (String)swrec.get("change");

			if (portnavn == null) portnavn = "";

			String boksbak = "";
			BoksMpBak bmp = (BoksMpBak)boksMp.get(boksid+":"+ifindex);
			Integer idbak = (bmp != null) ? bmp.boksbak : null;
			if (idbak != null) boksbak = (String)boksNavn.get(idbak);
			if (boksbak == null) {
				outl("ERROR! boksbak is null for idbak: " + idbak + "<br>");
				continue;
			}

			// P� grunn av altfor stort volum tas ikke KANT-bokser med tomt portnavn og boksbak med i listen
			if (boksKat.get(new Integer(boksid)) == null) {
				System.err.println("ERROR, boksKat is null for boksid: " + boksid);
				continue;
			}
			if (((String)boksKat.get(new Integer(boksid))).equalsIgnoreCase("edge") && portnavn.length() == 0 && boksbak.length() == 0) continue;

			String color = "gray";
			if (change != null && change.startsWith("Error")) {
				color = "red";
			} else
			if (portnavn.length() == 0 && boksbak.length()>0) {
				color = "blue";
			} else
			if (portnavn.length() > 0 && boksbak.length()==0) {
				if (portnavn.indexOf("-h") != -1 || portnavn.indexOf("-sw") != -1 || portnavn.indexOf("-gw") != -1) {
					color = "purple";
				}
			} else
			if (portnavn.length() > 0 && boksbak.length()>0 && portnavn.endsWith(boksbak) ) {
				color = "green";
			} else
			if (portnavn.length() > 0 && boksbak.length()>0 && !portnavn.endsWith(boksbak) ) {
				color = "red";
			}

			String color1 = "<font color="+color+">";
			String color2 = "</font>";

			outl("<tr><a name=\"" + swrec.get("swportid") + "\">");
			outl("<td align=right>"+color1+ swrec.get("swportid") + color2+"</td>");
			outl("<td align=right>"+color1+ swrec.get("netboxid") + color2+"</td>");
			outl("<td>"+color1+ boksNavn.get(new Integer((String)swrec.get("netboxid"))) + color2+"</td>");
			outl("<td align=right>"+color1+ swrec.get("speed") + color2+"</td>");
			outl("<td align=right>"+color1+ swrec.get("duplex") + color2+"</td>");
			outl("<td align=right>"+color1+ swrec.get("ifindex") + color2+"</td>");
			outl("<td>"+color1+ portnavn + color2+"</td>");
			outl("<td>"+color1+ boksbak + color2+"</td>");

			if (change != null) outl("<td><b>"+change+"</b></td>");

			outl("</tr>");
		}
		outl("</table>");

		//outl("New rows: <b>" + newcnt + "</b> Updated rows: <b>" + updcnt + "</b> Removed rows: <b>"+remcnt+"</b><br>");
		outl("New rows: <b>" + newcnt + "</b> Updated rows: <b>" + updcnt + "</b><br>");
		outl("Sum rows: <b>" + swport.size() + "</b><br>");
		/*
		if (newcnt > 0 || updcnt > 0 || resetcnt > 0) {
			if (DEBUG_OUT) outl("** COMMIT ON DATABASE **<br>");
			Database.commit();
		}
		*/
		//Database.rollback();


		outl("All done.<br>");

	}

	private HashMap getHashFromResultSet(ResultSet rs, ResultSetMetaData md) throws SQLException
	{
		HashMap hm = new HashMap();
		for (int i=md.getColumnCount(); i > 0; i--) {
			hm.put(md.getColumnName(i), rs.getString(i));
		}
		return hm;
	}

	/* [/ni.avledVlan]
	 *
	 */
	public void avledVlan() throws SQLException
	{
		boolean DB_UPDATE = true;
		boolean DB_COMMIT = true;
		boolean DEBUG_OUT = false;
		boolean TIME_OUT = true;

		long beginTime;

		//String debugParam = com.getp("debug");
		if (debugParam != null && debugParam.equals("yes")) DEBUG_OUT = true;
		if (DEBUG_OUT) outl("Begin<br>");

		// Vis dato
		{
			java.util.Date currentTime = new GregorianCalendar().getTime();
			outl("Generated on: <b>" + currentTime + "</b><br>");
		}

		// Vi starter med � sette boksbak til null alle steder hvor status='down', slik at vi unng�r l�kker
		{
			Database.update("UPDATE swport SET to_netboxid = NULL, to_swportid = NULL WHERE link!='y' AND to_netboxid IS NOT NULL");
			//if (DB_COMMIT) Database.commit(); // Vi ruller tilbake lenger ned i koden
		}

		// Find mapping for firewalled VLANs
		Map fwVlanMap = new HashMap();
		{
			beginTime = System.currentTimeMillis();
			ResultSet rs = Database.query("select vlan,netaddr from vlan join prefix using(vlanid) where vlan not in (select vlan from swport where vlan is not null) and nettype='lan' and prefixid in (select prefixid from arp where end_time='infinity' and mac not in (select mac from netboxmac))", true);
			while (rs.next()) {
				String vlan = rs.getString("vlan");
				String netaddr = rs.getString("netaddr");
				ResultSet rs2 = Database.query("select cam.sysname,cam.netboxid,cam.ifindex,vlan from arp join cam using(mac) join swport on (moduleid in (select moduleid from module where module.netboxid=cam.netboxid) and swport.ifindex=cam.ifindex) where ip << '" + netaddr + "' and cam.end_time='infinity' and arp.end_time='infinity' and (trunk=false or trunk is null) and vlan > 1");
				if (rs2.next()) {
					fwVlanMap.put(vlan, rs2.getString("vlan"));
				}
			}
			Database.free(rs);
			if (TIME_OUT) outl("Spent " + (System.currentTimeMillis()-beginTime) + " ms finding firewalled VLAN mappings (found " + fwVlanMap.size() + " mappings: " + fwVlanMap + ")<br>");
		}
		// select cam.sysname,cam.netboxid,cam.ifindex,vlan from arp join cam using(mac) join swport on (moduleid in (select moduleid from module where module.netboxid=cam.netboxid) and swport.ifindex=cam.ifindex) where ip << '129.241.23.0/26' and cam.end_time='infinity' and arp.end_time='infinity'and vlan > 1;

		beginTime = System.currentTimeMillis();

		Map dataStructs = new HashMap();

		// Denne er egentlig bare n�dvendig for debugging
		HashMap boksName = new HashMap();
		ResultSet rs = Database.query("SELECT netboxid,sysname FROM netbox");
		while (rs.next()) boksName.put(rs.getString("netboxid"), rs.getString("sysname"));

		Map vlanidVlan = new HashMap();
		Map vlanidNettype = new HashMap();
		rs = Database.query("SELECT vlanid,vlan,nettype FROM vlan");
		while (rs.next()) {
			if (rs.getString("vlan") != null) vlanidVlan.put(rs.getString("vlanid"), rs.getString("vlan"));
			vlanidNettype.put(rs.getString("vlanid"), rs.getString("nettype"));
		}

		// Trenger � vite hva som er GW, alle linker til slike er nemlig 'o' og de skal ikke traverseres
		HashSet boksGwSet = new HashSet();
		rs = Database.query("SELECT netboxid FROM netbox WHERE catid IN ('GW', 'v6GW')");
		while (rs.next()) boksGwSet.add(rs.getString("netboxid"));

		// Oversikt over hvilke vlan som kj�rer p� en swport mot gw
		Map swportGwVlanMap = new HashMap();
		rs = Database.query("SELECT DISTINCT to_swportid,vlan,gwportid FROM gwport JOIN gwportprefix USING(gwportid) JOIN prefix USING(prefixid) JOIN vlan USING(vlanid) JOIN module USING(moduleid) WHERE to_swportid IS NOT NULL AND vlan IS NOT NULL");
		while (rs.next()) swportGwVlanMap.put(rs.getString("to_swportid")+":"+rs.getString("vlan"), rs.getString("gwportid"));

		// Mapping from gwportid to the running vlanid and prefixid (needed for updating)
		Map gwportVlanidMap = new HashMap();
		rs = Database.query("SELECT DISTINCT gwportid,vlanid,netboxid FROM gwport JOIN gwportprefix USING(gwportid) JOIN prefix USING(prefixid) JOIN vlan USING(vlanid) JOIN module USING(moduleid) WHERE to_swportid IS NOT NULL");
		while (rs.next()) gwportVlanidMap.put(rs.getString("gwportid"), new String[] { rs.getString("vlanid"), rs.getString("netboxid") } );

		// Oversikt over hvilke linker:vlan som er blokkert av spanning tree
		HashSet spanTreeBlocked = new HashSet();
		rs = Database.query("SELECT swportid,vlan FROM swportblocked");
		while (rs.next()) spanTreeBlocked.add(rs.getString("swportid")+":"+rs.getString("vlan"));

		// Oversikt over ikke-trunker ut fra hver boks per vlan
		HashMap nontrunkVlan = new HashMap();
		//rs = Database.query("SELECT swportid,netboxid,to_netboxid,to_swportid,vlan FROM swport JOIN module USING(moduleid) WHERE (trunk='f' OR trunk IS NULL) AND to_netboxid IS NOT NULL AND vlan IS NOT NULL");
		rs = Database.query("SELECT swportid,netboxid,to_netboxid,to_swportid,COALESCE(vlan,1) AS vlan FROM swport JOIN module USING(moduleid) WHERE (trunk='f' OR trunk IS NULL) AND to_netboxid IS NOT NULL");
		while (rs.next()) {
			HashMap nontrunkMap;
			String key = rs.getString("netboxid")+":"+rs.getString("vlan");
			if ( (nontrunkMap = (HashMap)nontrunkVlan.get(key)) == null) {
				nontrunkMap = new HashMap();
				nontrunkVlan.put(key, nontrunkMap);
			}
			HashMap hm = new HashMap();
			hm.put("swportid", rs.getString("swportid"));
			//hm.put("to_netboxid", rs.getString("netboxid"));
			hm.put("netboxid", rs.getString("netboxid"));
			hm.put("to_netboxid", rs.getString("to_netboxid"));
			String toid = rs.getString("to_swportid") != null ? rs.getString("to_swportid") : rs.getString("to_netboxid");
			nontrunkMap.put(toid, hm);
		}

		// F�rst m� vi hente oversikten over hvilke vlan som kan kj�re p� de forskjellige portene
		HashMap allowedVlan = new HashMap();
		rs = Database.query("SELECT netboxid,swportid,module,port,to_netboxid,hexstring FROM swport JOIN module USING(moduleid) JOIN swportallowedvlan USING (swportid) WHERE to_netboxid IS NOT NULL ORDER BY to_netboxid");

		while (rs.next()) {
			HashMap boksAllowedMap;
			String boksid = rs.getString("netboxid");
			if ( (boksAllowedMap = (HashMap)allowedVlan.get(boksid)) == null) {
				boksAllowedMap = new HashMap();
				allowedVlan.put(boksid, boksAllowedMap);
			}
			HashMap hm = new HashMap();
			hm.put("swportid", rs.getString("swportid"));
			hm.put("netboxid", rs.getString("netboxid"));
			hm.put("module", rs.getString("module"));
			hm.put("port", rs.getString("port"));
			hm.put("to_netboxid", rs.getString("to_netboxid"));
			hm.put("hexstring", rs.getString("hexstring"));

			String boksbak = rs.getString("to_netboxid");
			if (boksAllowedMap.containsKey(boksbak)) outl("<font color=red>WARNING</font>: Multiple trunks between <b>"+boksName.get(boksid)+"</b> and <b>"+boksName.get(boksbak)+"</b><br>");
			boksAllowedMap.put(boksbak, hm);
		}

		// Vi trenger � vite hvilke vlan som g�r ut p� ikke-trunk fra en gitt boks
		// Bruker da en HashMap av HashSets
		HashMap activeVlan = new HashMap();
		// vlan er aktivt p� port selv om den er nede, og vi m� ta med vlan'et IP'en p� selve boksen er p�
		//rs = Database.query("(SELECT DISTINCT netboxid,vlan FROM swport JOIN module USING(moduleid) WHERE trunk='f' AND vlan IS NOT NULL) UNION (SELECT DISTINCT netboxid,vlan FROM netbox JOIN prefix USING(prefixid) JOIN vlan USING(vlanid) WHERE vlan IS NOT NULL)");
		rs = Database.query("SELECT DISTINCT swportid,netboxid,COALESCE(vlan,1) AS vlan FROM swport JOIN module USING(moduleid) WHERE (trunk='f' OR trunk IS NULL) AND to_netboxid IS NULL");
		while (rs.next()) {
			Map m;
			String netboxid = rs.getString("netboxid");
			if ((m = (Map)activeVlan.get(netboxid)) == null) activeVlan.put(netboxid, m = new HashMap());
			
			Set s;
			if ((s = (Set)m.get(new Integer(rs.getInt("vlan")))) == null) m.put(new Integer(rs.getInt("vlan")), s = new HashSet());
			s.add(rs.getString("swportid"));
		}

		// The VLAN of the netboxs' IP should also be added to activeVlan
		rs = Database.query("SELECT netboxid,vlan FROM netbox JOIN prefix USING(prefixid) JOIN vlan USING(vlanid) WHERE vlan IS NOT NULL");
		while (rs.next()) {
			Map m;
			String netboxid = rs.getString("netboxid");
			if ((m = (Map)activeVlan.get(netboxid)) == null) activeVlan.put(netboxid, m = new HashMap());

			Integer vl = new Integer(rs.getInt("vlan"));
			if (!m.containsKey(vl)) m.put(vl, new HashSet());
		}

		// Mapping over hvilken swport from befinner seg bak en swport
		HashMap swportidMap = new HashMap();
		rs = Database.query("SELECT swportid,COALESCE(vlan,1) AS vlan,to_swportid FROM swport WHERE (trunk='f' OR trunk IS NULL) AND to_swportid IS NOT NULL");
		while (rs.next()) {
			HashMap hm = new HashMap();
			hm.put("vlan", rs.getString("vlan"));
			hm.put("to_swportid", rs.getString("to_swportid"));
			swportidMap.put(rs.getString("swportid"), hm);
		}

		// Mapping av hvilket vlan som kj�rer mellom to bokser der vi ikke har to_swportid
		Map nbvlanMap = new HashMap();
		dataStructs.put("nbvlanMap", nbvlanMap);
		rs = Database.query("SELECT netboxid,to_netboxid,COALESCE(vlan,1) AS vlan FROM module JOIN swport USING(moduleid) WHERE (trunk='f' OR trunk IS NULL) AND to_netboxid IS NOT NULL AND to_swportid IS NULL ORDER BY netboxid");
		while (rs.next()) {
			String key = rs.getString("netboxid")+":"+rs.getString("to_netboxid");
			if (nbvlanMap.containsKey(key)) {
				outl("<font color=red>WARNING</font>: Multiple links between <b>"+boksName.get(rs.getString("netboxid"))+"</b> and <b>"+boksName.get(rs.getString("to_netboxid"))+" without exact swport knowledge (swportid)</b><br>");
			} else {
				nbvlanMap.put(key, rs.getString("vlan"));
			}
		}


		// Bruker cam/arp til � sjekke vlan bak netbox / ifindex (n�r vi kommer fra trunk)
		Map swportidVlanMap = new HashMap();
		Set swportidVlanDupeSet = new HashSet();
		dataStructs.put("swportidVlanMap", swportidVlanMap);
		//rs = Database.query("SELECT netbox.sysname,swport.ifindex,vlan.vlan FROM netbox JOIN module USING(netboxid) JOIN swport USING(moduleid) JOIN cam ON (netbox.netboxid = cam.netboxid AND swport.ifindex = cam.ifindex and cam.end_time = 'infinity') JOIN arp ON (cam.mac = arp.mac AND arp.end_time = 'infinity') JOIN prefix ON (arp.prefixid = prefix.prefixid) JOIN vlan USING(vlanid) GROUP BY netbox.sysname,swport.ifindex,vlan.vlan");
		rs = Database.query("SELECT swportid,vlanid,COUNT(*) AS count FROM module JOIN swport USING(moduleid) JOIN cam ON (module.netboxid = cam.netboxid AND swport.ifindex = cam.ifindex and cam.end_time = 'infinity') JOIN arp ON (cam.mac = arp.mac AND arp.end_time = 'infinity') JOIN prefix ON (arp.prefixid = prefix.prefixid) JOIN vlan USING(vlanid) WHERE (trunk='f' OR trunk IS NULL) GROUP BY swportid,vlanid ORDER BY swportid,count DESC");
		while (rs.next()) {
			String key = rs.getString("swportid")+":"+rs.getString("vlanid");
			if (swportidVlanDupeSet.add(key)) {
				swportidVlanMap.put(rs.getString("swportid"), rs.getString("vlanid"));
			} else {
				outl("<font color=red>WARNING</font>: Multiple VLANs detected behind non-trunk port (swportid="+rs.getString("swportid")+", vlanid="+rs.getString("vlanid")+")<br>");
			}
		}

		/*
		// All non-trunk swportids
		Set nontrunkSwportids = new HashSet();
		rs = Database.query("SELECT swportid FROM swport WHERE (trunk='f' OR trunk IS NULL)");
		while (rs.next()) {
			nontrunkSwportids.add(rs.getString("swportid"));
		}
		*/

		if (TIME_OUT) outl("Spent " + (System.currentTimeMillis()-beginTime) + " ms fetching data from db<br>");

		// S� henter vi ut alle vlan og hvilken switch vlanet "starter p�"
		outl("<pre>");
		//rs = Database.query("SELECT module.netboxid,vlan,netaddr,sysname,gwport.to_netboxid,gwport.to_swportid,trunk,hexstring FROM prefix JOIN gwport ON (rootgwid=gwportid) JOIN module USING(moduleid) JOIN netbox USING (netboxid) LEFT JOIN swport ON (gwport.to_swportid=swportid) LEFT JOIN swportallowedvlan USING (swportid) WHERE (gwport.to_netboxid IS NOT NULL OR catid='GSW') AND vlan IS NOT NULL ORDER BY vlan");

		beginTime = System.currentTimeMillis();
		rs = Database.query("SELECT DISTINCT module.netboxid,vlanid,vlan.vlan,sysname,gwportid,gwport.to_netboxid,gwport.to_swportid,trunk,hexstring FROM prefix JOIN vlan USING(vlanid) JOIN gwportprefix ON (prefix.prefixid = gwportprefix.prefixid AND (hsrp='t' OR gwip::text IN (SELECT MIN(gwip::text) FROM gwportprefix GROUP BY prefixid HAVING COUNT(DISTINCT hsrp) = 1))) JOIN gwport USING(gwportid) JOIN module USING(moduleid) JOIN netbox USING (netboxid) LEFT JOIN swport ON (gwport.to_swportid=swportid) LEFT JOIN swportallowedvlan USING (swportid) WHERE (gwport.to_netboxid IS NOT NULL OR catid='GSW') AND vlan.vlan IS NOT NULL ORDER BY vlan.vlan");

		Set vlansWithRouter = new HashSet();
		while (rs.next()) {
			vlansWithRouter.add(rs.getString("vlan"));
		}
		rs.beforeFirst();

		ArrayList trunkVlan = new ArrayList();
		Set doneVlan = new HashSet();
		Set visitedNodeSet = new HashSet(); // Settet av noder vi har bes�kt; resettes for hvert vlan
		Set foundGwSet = new HashSet();
		// ***** BEGIN DEPTH FIRST SEARCH ***** //
		while (rs.next()) {
			int vlan = rs.getInt("vlan");
			if (fwVlanMap.containsKey(""+vlan) && !vlansWithRouter.contains(fwVlanMap.get(""+vlan))) {
				if (DEBUG_OUT) outl("Mapping vlan " + vlan + " to " + fwVlanMap.get(""+vlan));
				vlan = Integer.parseInt((String)fwVlanMap.get(""+vlan));
			}
			int vlanid = rs.getInt("vlanid");
 			String boksid = rs.getString("netboxid");
			String nettype = (String)vlanidNettype.get(""+vlanid);
			doneVlan.add(""+vlan);
			/*
			if (!doneVlan.add(new Integer(vlanid))) {
				// Duplicate vlanid, check if we already found this gw
				if (foundGwSet.contains(boksid+":"+vlanid)) continue;
				// Now we need to split the vlan
				String[] ins = {
					"vlanid", "",
					"vlan", rs.getString("vlan"),
					"nettype", nettype
				};
				int oldVlanid = vlanid;
				vlanid = Integer.parseInt(Database.insert("vlan", ins, null));
				System.err.println("Splitting vlan: " + rs.getString("vlan") + " ("+oldVlanid+"), new vlanid: " + vlanid + ", gwportid: " + rs.getString("gwportid"));
				Database.update("UPDATE prefix SET vlanid="+vlanid+" WHERE prefixid IN (SELECT prefixid FROM gwportprefix WHERE gwportid="+rs.getString("gwportid")+")");
			}
			*/
			visitedNodeSet.clear();

			//String netaddr = rs.getString("netaddr");
			String netaddr = "NA";
			String boksbak = rs.getString("to_netboxid");
			if (boksbak == null || boksbak.length() == 0) boksbak = boksid; // Spesialtilfelle for GSW enheter
			String swportbak = rs.getString("to_swportid");
			boolean cameFromTrunk = rs.getBoolean("trunk");
			String hexstring = rs.getString("hexstring");
			if (DEBUG_OUT) outl("\n<b>NEW VLAN: " + vlan + "</b> (netaddr: <b>"+netaddr+"</b>)<br>");

			// Sjekk om det er en trunk eller ikke-trunk ned til gw'en
			if (cameFromTrunk) {
				// N� forventer vi at hexstring er p� plass
				if (hexstring == null) {
					if (DEBUG_OUT) outl("\n<b>AllowedVlan hexstring for trunk down to switch is missing, skipping...</b><br>");
					continue;
				}
				// Sjekk vi om vi faktisk har lov til � kj�re p� trunken
				if (!isAllowedVlan(hexstring, vlan)) {
					if (DEBUG_OUT) outl("\n<b>Vlan is not allowed on trunk down to switch, and there is no non-trunk, skipping...</b><br>");
					continue;
				}
			}

			/*
			// Vi m� n� sjekke om det er en ikke-trunk opp fra switchen til denne gw'en p� dette vlan'et
			String key = boksbak+":"+vlan;
			HashMap nontrunkMap = (HashMap)nontrunkVlan.get(key);
			if (nontrunkMap != null) {
				// Det er porter p� vlanet ihvertfall, men er det noen til gw'en?
				HashMap swrec = (HashMap)nontrunkMap.get(boksid);
				if (swrec != null) {
					// Jo, ok, da lagrer vi den virkelige swportid'en
					 swportid = (String)swrec.get("swportid");
					 cameFromTrunk = false;
				 }
			 }
			 if (cameFromTrunk) {
				 // Det er ikke en ikke-trunk mellom gw og sw, alts� m� det v�re en trunk
				 // Da m� vi f�rst sjekke at vlanet har lov til � kj�re
				if (rs.getString("hexstring") == null) {
					if (DEBUG_OUT) outl("\n<b>AllowedVlan hexstring for trunk down to switch is missing, and there is no non-trunk, skipping...</b><br>");
					continue;
				} else if (!isAllowedVlan(rs.getString("hexstring"), vlan)) {
					if (DEBUG_OUT) outl("\n<b>Vlan is not allowed on trunk down to switch, and there is no non-trunk, skipping...</b><br>");
					continue;
				}
				// OK, vi har lov til � kj�re p� trunken, lagre swportid for denne
				swportid = rs.getString("swportid");
			}
			*/

			// S� traverserer vi linken ned til sw'en

			//  vlanTraverseLink(int vlan, String fromid, String boksid, boolean cameFromTrunk, boolean setDirection, HashMap nontrunkVlan, HashMap allowedVlan, HashMap activeVlan, HashSet spanTreeBlocked, ArrayList trunkVlan, HashSet visitNode, int level, Com com, boolean DEBUG_OUT, HashMap boksName)
			
			// List of gwports we have uplink to
			List foundGwports = new ArrayList();

			if (vlanTraverseLink(vlan, vlanid, boksid, boksbak, cameFromTrunk, true, nontrunkVlan, allowedVlan, activeVlan, swportidMap, spanTreeBlocked, trunkVlan, dataStructs, foundGwports, visitedNodeSet, 0, DEBUG_OUT, boksGwSet, swportGwVlanMap, boksName)) {

				// Vlanet er aktivt p� enheten, s� da legger vi det til
				if (swportbak != null) {
					String[] tvlan = {
						swportbak,
						String.valueOf(vlanid),
						"o"
					};
					trunkVlan.add(tvlan);
				}

				// If any gwports use a different vlanid we must change it to the current one
				for (Iterator it = foundGwports.iterator(); it.hasNext();) {
					String gwportid = (String)it.next();
					String[] vlanPrefix = (String[])gwportVlanidMap.get(gwportid);
					String oldVlanid = vlanPrefix[0];
					String gwNetboxid = vlanPrefix[1];
					foundGwSet.add(gwNetboxid+":"+vlanid);
					if (vlanid != Integer.parseInt(oldVlanid)) {
						// Swap in prefix
						Database.update("UPDATE prefix SET vlanid="+vlanid+" WHERE prefixid IN (SELECT prefixid FROM gwportprefix WHERE gwportid="+gwportid+")");
					}
				}
			}


			/*
			boolean b = false;
			for (Iterator i=trunkVlan.iterator(); i.hasNext();) {
				String[] s = (String[])i.next();
				if (s[0].equals("94095")) {
					errl("Wops, 94095, vlan: " + s[1] + " retning: " + s[2]);
					b = true;
				}
			}
			if (b) errl("");
			*/

		}
		outl("</pre>");

		if (TIME_OUT) outl("Spent " + (System.currentTimeMillis()-beginTime) + " ms traversing VLANs from router<br>");

		outl("\n<b>VLANs with no router to start from:</b><br>");
		outl("<pre>");

		updateVlanDb(trunkVlan, vlanidVlan, allowedVlan, boksName, false);

		beginTime = System.currentTimeMillis();

		// Alle vlan som vi ikke finner startpunkt p�, hver m� vi rett og slett starte alle andre steder for � v�re sikker p� � f� med alt
		// SELECT DISTINCT ON (vlan,boksid) boksid,modul,port,boksbak,vlan,trunk FROM swport NATURAL JOIN swportvlan WHERE vlan NOT IN (SELECT DISTINCT vlan FROM (prefiks JOIN gwport USING (prefiksid)) JOIN boks USING (boksid) WHERE boksbak IS NOT NULL AND vlan IS NOT NULL) AND boksbak IS NOT NULL ORDER BY vlan,boksid
		if (DEBUG_OUT) outl("\n<b><h3>VLANs with no router to start from:</h3></b><br>");
		/*
		//rs = Database.query("SELECT DISTINCT ON (vlan,boksid) vlan,sysname,boksbak FROM swport NATURAL JOIN swportvlan JOIN boks USING (boksid) WHERE vlan NOT IN (SELECT DISTINCT vlan FROM (prefiks JOIN gwport USING (prefiksid)) JOIN boks USING (boksid) WHERE boksbak IS NOT NULL AND vlan IS NOT NULL) AND boksbak IS NOT NULL ORDER BY vlan");
		rs = Database.query("SELECT DISTINCT ON (vlanid,module.netboxid) vlan,vlanid,sysname,to_netboxid FROM swport JOIN module USING(moduleid) JOIN swportvlan USING(swportid) JOIN netbox ON (to_netboxid=netbox.netboxid) WHERE vlan NOT IN (SELECT DISTINCT vlan FROM prefix JOIN gwportprefix USING(prefixid) JOIN gwport USING (gwportid) WHERE to_netboxid IS NOT NULL AND vlan IS NOT NULL) AND to_netboxid IS NOT NULL ORDER BY vlanid");
		HashSet visitNode = null;
		int prevVlanid=-1;
		while (rs.next()) {
			int vlan = rs.getInt("vlan");
			int vlanid = rs.getInt("vlanid");
			if (doneVlan.contains(new Integer(vlanid))) {
				//errl("Vlan " + vlan + " already processed");
				continue;
			}
			if (vlanid != prevVlanid) {
				visitNode = new HashSet();
				prevVlanid = vlanid;
			}
			if (DEBUG_OUT) outl("\n<b>NEW VLAN: " + vlan + "</b>, starting from <b>"+rs.getString("sysname")+"</b> ("+rs.getString("to_netboxid")+")<br>");
			vlanTraverseLink(vlan, vlanid, null, rs.getString("to_netboxid"), true, false, nontrunkVlan, allowedVlan, activeVlan, swportidMap, spanTreeBlocked, trunkVlan, dataStructs, new ArrayList(), visitNode, 0, DEBUG_OUT, boksGwSet, swportGwVlanMap, boksName);
		}
		*/
		{
			// Delete mismatching ports
			// DELETE FROM swport WHERE swportid IN (SELECT swportid FROM swport JOIN swportvlan USING(swportid) JOIN vlan USING(vlanid) WHERE vlan.vlan != swport.vlan AND direction IN ('x','u'))
			String[] vlansDone = util.stringArray(doneVlan);
			Arrays.sort(vlansDone);
			//String sql = "SELECT swportid,vlan,vlanid,sysname,to_netboxid,to_swportid,trunk FROM swport JOIN module USING(moduleid) JOIN netbox ON (to_netboxid=netbox.netboxid) LEFT JOIN swportvlan USING(swportid) WHERE vlan NOT IN (" + util.join(vlansDone, ",") + ") AND to_netboxid IS NOT NULL AND vlan IS NOT NULL AND (direction IS NULL OR direction IN ('x','u')) ORDER BY vlan, vlanid";
			String sql = "SELECT DISTINCT netboxid,vlan,vlanid,sysname FROM swport JOIN module USING(moduleid) JOIN netbox USING (netboxid) LEFT JOIN swportvlan USING(swportid) WHERE vlan NOT IN (" + util.join(vlansDone, ",") + ") AND vlan IS NOT NULL AND trunk!=TRUE AND (direction IS NULL OR direction IN ('x','u')) ORDER BY vlan, vlanid";
			rs = Database.query(sql);
			outl("SQL: " + sql);
			int prevvlan=-1;
			int vlanid = -1;
			HashSet visitNode = null;
			while (rs.next()) {
				int vlan = rs.getInt("vlan");
				if (vlan != prevvlan) {
					visitNode = new HashSet();
					prevvlan = vlan;
					vlanid = rs.getInt("vlanid");
					if (vlanid == 0) {
						String[] ins = new String[] {
							"vlanid", "",
							"vlan", ""+vlan,
							"nettype", "lan"
						};
						vlanid = Integer.parseInt(Database.insert("vlan", ins, null));
						vlanidVlan.put(""+vlanid, ""+vlan);
						outl("\n<b>CREATE NEW VLAN: " + vlan + "</b>, vlanid="+vlanid+", starting from <b>"+rs.getString("sysname")+"</b><br>");
					} else {
						outl("\n<b>NEW VLAN: " + vlan + "</b>, vlanid="+vlanid+", starting from <b>"+rs.getString("sysname")+"</b><br>");
					}
				}
				if (visitNode.contains(rs.getString("netboxid"))) continue;
				vlanTraverseLink(vlan, vlanid, null, rs.getString("netboxid"), false, false, nontrunkVlan, allowedVlan, activeVlan, swportidMap, spanTreeBlocked, trunkVlan, dataStructs, new ArrayList(), visitNode, 0, DEBUG_OUT, boksGwSet, swportGwVlanMap, boksName);

				/*
				if (rs.getBoolean("trunk") == false) {
					// Always set active for non-trunk
					String[] rVlan = {
						rs.getString("swportid"),
						String.valueOf(vlanid),
						"u"
					};
					trunkVlan.add(rVlan);
					
					String to_swportid = rs.getString("to_swportid");
					if (to_swportid != null) {
						String[] tVlan = {
							to_swportid,
							String.valueOf(vlanid),
							"u"
						};
						trunkVlan.add(tVlan);
					}
				}
				*/

			}
		}

		outl("</pre>");
		if (TIME_OUT) outl("Spent " + (System.currentTimeMillis()-beginTime) + " ms traversing VLANs with no router<br>");

		Map activeOnTrunk = updateVlanDb(trunkVlan, vlanidVlan, allowedVlan, boksName, true);

		// S� skriver vi ut en rapport om mismatch mellom swportallowedvlan og det som faktisk kj�rer
		outl("<h2>Allowed, but non-active VLANs:</h2>");
		outl("<h4>(<i><b>Note</b>: VLANs 1 and 1000-1005 are for interswitch control traffic and are always allowed</i>)</h4>");
		int allowedcnt=0, totcnt=0;
		Iterator iter = allowedVlan.values().iterator();
		while (iter.hasNext()) {
			HashMap boksAllowedMap = (HashMap)iter.next();
			Iterator iter2 = boksAllowedMap.values().iterator();
			while (iter2.hasNext()) {
				HashMap hm = (HashMap)iter2.next();
				String swportid = (String)hm.get("swportid");
				String hexstring = (String)hm.get("hexstring");

				HashSet activeVlanOnTrunk = (HashSet)activeOnTrunk.get(swportid);
				if (activeVlanOnTrunk == null) {
					//outl("ERROR, swrecTrunk is missing for swportid: " + swportid + "<br>");
					continue;
				}
				totcnt++;

				String boksid = (String)hm.get("netboxid");
				String modul = (String)hm.get("module");
				String port = (String)hm.get("port");
				String boksbak = (String)hm.get("to_netboxid");
				boolean printMsg = false;

				int startRange=0;
				boolean markLast=false;
				int MIN_VLAN = 2;
				int MAX_VLAN = 999;
				for (int i=MIN_VLAN; i <= MAX_VLAN+1; i++) {
					if (isAllowedVlan(hexstring, i) && !activeVlanOnTrunk.contains(String.valueOf(i)) && i != MAX_VLAN+1 ) {
						if (!markLast) {
							startRange=i;
							markLast = true;
						}
					} else {
						if (markLast) {
							String range = (startRange==i-1) ? String.valueOf(i-1) : startRange+"-"+(i-1);
							if (!printMsg) {
								allowedcnt++;
								outl("Working with trunk From("+boksid+"): <b>"+boksName.get(boksid)+"</b>, Modul: <b>"+modul+"</b> Port: <b>"+port+"</b> To("+boksbak+"): <b>"+boksName.get(boksbak)+"</b><br>");
								// Skriv ut aktive vlan
								out("&nbsp;&nbsp;Active VLANs: <b>");
								Iterator vlanIter = activeVlanOnTrunk.iterator();
								int[] vlanA = new int[activeVlanOnTrunk.size()];
								int vlanAi=0;
								while (vlanIter.hasNext()) vlanA[vlanAi++] = Integer.parseInt((String)vlanIter.next());
								Arrays.sort(vlanA);
								boolean first=true;
								for (vlanAi=0; vlanAi < vlanA.length; vlanAi++) {
									if (!first) out(", "); else first=false;
									out(String.valueOf(vlanA[vlanAi]));
								}
								outl("</b><br>");
								//outl("&nbsp;&nbsp;The following VLANs are allowed on the trunk, but does not seem to be active:<br>");
								printMsg = true;
								out("&nbsp;&nbsp;Excessive VLANs: <b>"+range+"</b>");
							} else {
								out(", <b>"+range+"</b>");
							}
							markLast=false;
						}
						//startRange=i+1;
					}
				}
				if (printMsg) outl("<br><br>");
			}
		}

		outl("A total of <b>"+allowedcnt+"</b> / <b>"+totcnt+"</b> trunks have allowed VLANs that are not active.<br>");

		// Send event to eventengine
		Map varMap = new HashMap();
		varMap.put("command", "updateFromDB");
		EventQ.createAndPostEvent("getDeviceData", "eventEngine", 0, 0, 0, "notification", Event.STATE_NONE, 0, 0, varMap);

		outl("All done.<br>");

	}

	public Map updateVlanDb(List trunkVlan, Map vlanidVlan, Map allowedVlan, Map boksName, boolean deleteNoDirection) throws SQLException {
		HashMap swportvlan = new HashMap();
		HashMap swportvlanNontrunk = new HashMap();
		HashMap swportvlanDupe = new HashMap();
		//rs = Database.query("SELECT swportvlanid,swportid,vlan,retning FROM swportvlan JOIN swport USING (swportid) WHERE swport.trunk='t'");
		String sql = "SELECT swportvlanid,swportid,vlanid,direction,trunk FROM swportvlan JOIN swport USING (swportid)";
		ResultSet rs = Database.query(sql);
		HashSet reportMultipleVlan = new HashSet();
		while (rs.next()) {
			String swportid = rs.getString("swportid");
			String key = swportid+":"+rs.getString("vlanid");
			swportvlanDupe.put(key, rs.getString("direction") );
			swportvlan.put(key, rs.getString("swportvlanid") );

			if (!rs.getBoolean("trunk")) {
				if (swportvlanNontrunk.containsKey(swportid)) {
					if (!reportMultipleVlan.contains(swportid)) {
						outl("<font color=\"red\">ERROR!</font> Multiple vlans for non-trunk port, swportid: " + key + "<br>");
						reportMultipleVlan.add(swportid);
					}
					continue;
				}
				swportvlanNontrunk.put(swportid, rs.getString("swportvlanid") );
			}
		}

		outl("<br><b>Report:</b> (found "+trunkVlan.size()+" records)<br>");

		HashMap activeOnTrunk = new HashMap(); // Denne brukes for � sjekke swportallowedvlan mot det som faktisk kj�rer

		int newcnt=0,updcnt=0,dupcnt=0,remcnt=0,renamecnt=0;
		for (int i=0; i < trunkVlan.size(); i++) {
			String[] s = (String[])trunkVlan.get(i);
			String swportid = s[0];
			String vlanid = s[1];
			String vlan = (String)vlanidVlan.get(vlanid);
			String direction = s[2];
			String key = swportid+":"+vlanid;

			if (swportvlanDupe.containsKey(key)) {
				// Elementet eksisterer i databasen fra f�r, s� vi skal ikke sette det inn
				// Sjekk om vi skal oppdatere
				String dbRetning = (String)swportvlanDupe.get(key);
				if (!dbRetning.equals(direction)) {
					// Oppdatering n�dvendig
					String[] updateFields = {
						"direction", direction
					};
					String[] condFields = {
						"swportid", swportid,
						"vlanid", vlanid
					};
					Database.update("swportvlan", updateFields, condFields);
					outl("[UPD] swportid: " + swportid + " vlan: <b>"+ vlan +"</b> Direction: <b>" + direction + "</b> (old: "+dbRetning+")<br>");
					updcnt++;
				} else {
					dupcnt++;
				}
				// Vi skal ikke slette denne recorden n�
				swportvlan.remove(key);


			} else {
				// Dette kan v�re en nontrunk port der vi har skrevet om vlan
				if (swportvlanNontrunk.containsKey(swportid)) {
					// Jepp, da oppdaterer vi bare
					updcnt++;
					outl("[UPD] swportid: " + swportid + " vlan: <b>"+ vlan +"</b> Direction: <b>" + direction + "</b> (renamed)<br>");

					String swportvlanid = (String)swportvlanNontrunk.get(swportid);
					String[] updateFields = {
						"vlanid", vlanid,
						"direction", direction
					};
					String[] condFields = {
						"swportvlanid",
						swportvlanid
					};
					Database.update("swportvlan", updateFields, condFields);

				} else {
					// swportvlan inneholder ikke dette innslaget fra f�r, s� vi m� sette det inn
					newcnt++;
					swportvlanDupe.put(key, direction);
					outl("[NEW] swportid: " + swportid + " vlan: <b>"+ vlan +"</b> Retning: <b>" + direction + "</b><br>");

					// Sett inn i swportvlan
					String[] fields = {
						"swportid", swportid,
						"vlanid", vlanid,
						"direction", direction,
					};
					Database.insert("swportvlan", fields);
				}
			}

			// S� legger vi til i activeOnTrunk
			//HashMap swrecTrunk;
			HashSet activeVlanOnTrunk;
			if ( (activeVlanOnTrunk = (HashSet)activeOnTrunk.get(swportid)) == null) {
				activeVlanOnTrunk = new HashSet();
				activeOnTrunk.put(swportid, activeVlanOnTrunk);
			}
			if (vlan == null) {
				System.err.println("WARNING: vlan is null for vlanid: " + vlanid);
				vlan = "-1";
			}
			activeVlanOnTrunk.add(vlan);
		}

		// N� kan vi g� gjennom swportvlan og slette de innslagene som ikke lenger eksisterer
		Iterator iter = swportvlan.entrySet().iterator();
		while (iter.hasNext()) {
			remcnt++;
			Map.Entry me = (Map.Entry)iter.next();
			String key = (String)me.getKey();
			String swportvlanid = (String)me.getValue();
				
			StringTokenizer st = new StringTokenizer(key, ":");
			String swportid = st.nextToken();
			String vlanid = st.nextToken();
			String vlan = (String)vlanidVlan.get(vlanid);

			if (!deleteNoDirection) {
				String direction = (String) swportvlanDupe.get(key);
				if ("x".equals(direction) || "u".equals(direction)) continue;
			}
			
			outl("[REM] swportid: " + swportid + " vlan: <b>"+ vlan +"</b> ("+swportvlanid+")<br>");
			Database.update("DELETE FROM swportvlan WHERE swportvlanid = '"+swportvlanid+"'");
		}

		/*
		// Til slutt g�r vi gjennom vlanRename og renamer alle vlan der det m� gj�res
		outl("Rename size: " + vlanRename.size());
		iter = vlanRename.iterator();
		while (iter.hasNext()) {
			HashMap vlanRenameEntry = (HashMap)iter.next();
			String boksid = (String)vlanRenameEntry.get("netboxid");
			String oldvlan = (String)vlanRenameEntry.get("oldvlan");
			String newvlanid = (String)vlanRenameEntry.get("newvlanid");

			if (DB_UPDATE) Database.update("UPDATE swportvlan SET vlanid='"+newvlanid+"' WHERE swportid IN (SELECT swportid FROM swport JOIN module USING(moduleid) WHERE netboxid='"+boksid+"' AND trunk='f' AND vlan='"+oldvlan+"')");

			//if (DB_COMMIT) Database.commit(); else Database.rollback();
			System.err.println("On boks: " + boksName.get(boksid) + " rename vlan: " + oldvlan + " to " + newvlan);

			renamecnt++;
		}
		renamecnt += vlanRename.size();
		*/

		// Then we delete all vlans without either prefices or swports
		int delPrefix = Database.update("DELETE FROM prefix WHERE prefixid NOT IN (SELECT prefixid FROM gwportprefix) AND vlanid NOT IN (SELECT vlanid FROM vlan JOIN swportvlan USING(vlanid) UNION SELECT vlanid FROM vlan WHERE nettype='scope')");
		int delVlan = Database.update("DELETE FROM vlan WHERE vlanid NOT IN (SELECT vlanid FROM prefix UNION SELECT vlanid FROM swportvlan UNION SELECT vlanid FROM vlan WHERE nettype='scope')");
		//if (newcnt > 0 || updcnt > 0 || remcnt > 0 || renamecnt > 0 || unusedCnt > 0) if (DB_COMMIT) Database.commit(); else Database.rollback();
		outl("New count: <b>"+newcnt+"</b>, Update count: <b>"+updcnt+"</b> Dup count: <b>"+dupcnt+"</b>, Rem count: <b>"+remcnt+"</b> delPrefix: <b>"+delPrefix+"</b>, delVlan: <b>"+delVlan+"</b>, Rename vlan count: <b>"+renamecnt+"</b><br>");

		//if (!DB_COMMIT) Database.rollback();

		return activeOnTrunk;
	}

	//private boolean vlanTraverseLink(int vlan, String fromid, String boksid, boolean cameFromTrunk, boolean setDirection, HashMap nontrunkVlan, HashMap allowedVlan, HashMap activeVlan, HashMap swportidMap, HashSet spanTreeBlocked, ArrayList trunkVlan, HashSet visitNode, int level, Com com, boolean DEBUG_OUT, HashSet boksGwSet, HashSet swportGwVlanSet, HashMap boksName)
	private boolean vlanTraverseLink(int vlan,
																	 int vlanid,
																	 String fromid,
																	 String boksid,
																	 boolean cameFromTrunk,
																	 boolean setDirection,
																	 HashMap nontrunkVlan,
																	 HashMap allowedVlan,
																	 HashMap activeVlan,
																	 HashMap swportidMap,
																	 HashSet spanTreeBlocked,
																	 List trunkVlan,
																	 Map dataStructs,
																	 List foundGwports,
																	 Set visitedNodeSet,
																	 int level,
																	 boolean DEBUG_OUT,
																	 HashSet boksGwSet,
																	 Map swportGwVlanMap,
																	 HashMap boksName)
	{
		if (level > 60) {
			outl("<font color=\"red\">ERROR! Level is way too big...</font>");
			return false;
		}
		String pad = "";
		for (int i=0; i<level; i++) pad+="        ";

		if (DEBUG_OUT) outl(pad+"><font color=\"green\">[ENTER]</font> Now at node("+boksid+"): <b>" + boksName.get(boksid) + "</b>, came from("+fromid+"): " + boksName.get(fromid) + ", vlan: " + vlan + " cameFromTrunk: <b>"+cameFromTrunk+"</b> level: <b>" + level + "</b>");

		// Sjekker for l�kker, trenger kun � traversere til samme enhet en gang
		if (visitedNodeSet.contains(boksid)) {
			if (DEBUG_OUT) outl(pad+"><font color=\"red\">[RETURN]</font> NOTICE: Found loop, from("+fromid+"): " + boksName.get(fromid) + ", boksid("+boksid+"): " + boksName.get(boksid) + ", vlan: " + vlan + ", level: " + level + "");
			return false;
		}
		visitedNodeSet.add(boksid);

		// Vi vet n� at dette vlanet kj�rer p� denne boksen, det f�rste vi gj�r da er � traversere videre
		// p� alle ikke-trunker og markerer retningen
		//HashSet foundGwUplinkSet = new HashSet(); // En boks kan kun ha en uplink til samme gw p� et gitt vlan
		boolean isActiveVlan = false;
		if (nontrunkVlan.containsKey(boksid+":"+vlan)) {
			String key = boksid+":"+vlan;
			HashMap nontrunkMap = (HashMap)nontrunkVlan.get(key);
			
			Iterator iter = nontrunkMap.values().iterator();
			while (iter.hasNext()) {
				HashMap hm = (HashMap)iter.next();
				String toid = (String)hm.get("to_netboxid");
				String swportid = (String)hm.get("swportid");
				String swportidBack = null;
				
				// Linken tilbake skal vi ikke f�lge uansett
				if (toid.equals(fromid)) continue;
				
				//select swportbak,vlan,boksid,interf from gwport join prefiks using(prefiksid) where swportbak is not null order by swportbak,vlan,boksid,interf;
				//select swportbak,vlan from gwport join prefiks using(prefiksid) where swportbak is not null and vlan is not null order by vlan,swportbak;
				
				if (boksGwSet.contains(toid)) {
					/*
						if (foundGwUplinkSet.contains(toid)) {
						// Hmm, vi har visst funnet denne f�r, dette kan egentlig ikke skje
						if (DEBUG_OUT) outl(pad+"--><font color=\"red\">[DUP-GW]</font> Error, found two non-trunk uplinks to gw, should not happen. boksid("+boksid+"): " + boksName.get(boksid) + ", to("+toid+"): " + boksName.get(toid) + ", vlan: " + vlan + ", level: <b>" + level + "</b> (<b>"+swportid+"</b>)");
						continue;
						}
					*/
					// Link til GW, vi skal ikke traversere, sjekk om dette vlanet g�r p� denne swporten
					if (swportGwVlanMap.containsKey(swportid+":"+vlan)) {
						// OK, linken blir da 'o'
						String[] rVlan = {
							swportid,
							String.valueOf(vlanid),
							(setDirection)?"o":"u"
						};
						if (DEBUG_OUT) outl(pad+"--><b>[NON-TRUNK-GW]</b> Running on non-trunk, vlan: <b>" + vlan + "</b>, boksid("+boksid+"): <b>" + boksName.get(boksid) + "</b>, to("+toid+"): <b>" + boksName.get(toid) + "</b> level: <b>" + level + "</b> (<b>"+rVlan[0]+"</b>)");
						trunkVlan.add(rVlan);
						isActiveVlan = true;
						foundGwports.add(swportGwVlanMap.get(swportid+":"+vlan));
					}
					continue;
				}

				// F�r vi traverserer linken ned s� sjekker vi f�rst vlanet p�
				// porten som g�r andre veien. Dersom det er ulikt m� vi
				// skrive om alle porter med nevnte vlan til det vi
				// traverserer for �yeblikket.
				String vlanBack = null;
				Map nbvlanMap = (Map)dataStructs.get("nbvlanMap"); // Mapper id:toid -> vlan

				if (swportidMap.containsKey(swportid)) {
					// Hent swport-recorden og hent to_swportid fra den
					Map mySwrec = (Map)swportidMap.get(swportid);
					swportidBack = (String)mySwrec.get("to_swportid");
					Map swrecBack = (Map)swportidMap.get(swportidBack);
					if (swrecBack != null) {
						vlanBack = (String)swrecBack.get("vlan");
					}
				}

				if (vlanBack == null) {
					// Just use ids
					vlanBack = (String)nbvlanMap.get(toid+":"+boksid);
				}

				// Det kan tenkes at andre enden har satt et annet vlan p� porten tilbake til denne enheten, og da skal vi skrive om vlan-nummer
				// Men kun hvis vi kommer ovenfra og ned, alts� hvis setDirection
				if (setDirection && vlan != 1 && nontrunkVlan.containsKey(toid+":"+vlanBack)) {
					HashMap nontrunkMapBack = (HashMap)nontrunkVlan.get(toid+":"+vlanBack);
					String idBack = (nontrunkMapBack != null && nontrunkMapBack.containsKey(swportid)) ? swportid : boksid;
					if (nontrunkMapBack != null && nontrunkMapBack.containsKey(idBack)) {
						// Vi har funnet link tilbake p� vlan (1 eller vlanBack), da bytter vi rett og slett ut
						nontrunkVlan.remove(toid+":"+vlanBack);
						nontrunkVlan.put(toid+":"+vlan, nontrunkMapBack);

						// Ogs� bytt ut i activeVlan
						Map map = (Map)activeVlan.get(toid);
						if (map != null && map.containsKey(new Integer(vlanBack))) {
							Collection c;
							if ((c = (Collection)map.get(new Integer(vlan))) == null) map.put(new Integer(vlan), c = new HashSet());
							c.addAll((Collection)map.remove(new Integer(vlanBack)));
						}

						/*
						HashMap vlanRenameEntry = new HashMap();
						vlanRenameEntry.put("netboxid", toid);
						vlanRenameEntry.put("oldvlan", vlanBack);
						vlanRenameEntry.put("newvlanid", String.valueOf(vlanid));
						vlanRename.add(vlanRenameEntry);
						*/

						if (DEBUG_OUT) outl(pad+"--><b>[REPLACE]</b> Replaced vlan: <b>1</b> with vlan: <b>" + vlan + "</b>, for boks("+toid+"): <b>" + boksName.get(toid) + "</b> level: <b>" + level + "</b>");
					}
				}

				// Vi kan n� legge til at retningen skal v�re ned her ihvertfall
				String[] rVlan = {
					swportid,
					String.valueOf(vlanid),
					(setDirection)?"n":"u"
				};
				trunkVlan.add(rVlan);
				isActiveVlan = true;

				if (DEBUG_OUT) outl(pad+"--><b>[NON-TRUNK]</b> Running on non-trunk, vlan: <b>" + vlan + "</b>, boksid("+boksid+"): <b>" + boksName.get(boksid) + "</b>, to("+toid+"): <b>" + boksName.get(toid) + "</b> level: <b>" + level + "</b> (<b>"+rVlan[0]+"</b>)");

				// S� traverserer vi linken, return-verdien her er uten betydning
				vlanTraverseLink(vlan, vlanid, boksid, toid, false, setDirection, nontrunkVlan, allowedVlan, activeVlan, swportidMap, spanTreeBlocked, trunkVlan, dataStructs, foundGwports, visitedNodeSet, level+1, DEBUG_OUT, boksGwSet, swportGwVlanMap, boksName);

				// S� sjekker vi om vi finner linken tilbake, i s� tilfellet skal den markeres med retning 'o'
				if (swportidBack == null) {
					String keyBack = toid+":"+vlan;
					HashMap nontrunkMapBack = (HashMap)nontrunkVlan.get(keyBack);
					if (nontrunkMapBack == null) {
						// Boksen vi ser p� har ingen non-trunk linker, og vi kan derfor g� videre
						if (DEBUG_OUT) outl(pad+"---->ERROR! No non-trunk links found for vlan: " + vlan + ", toid("+toid+"): " + boksName.get(toid) + ", level: " + level + "");
						continue;
					}
					
					HashMap hmBack = (HashMap)nontrunkMapBack.get(boksid);
					if (hmBack == null) {
						// Linken tilbake mangler
						if (DEBUG_OUT) outl(pad+"---->ERROR! Link back not found for vlan: " + vlan + ", toid("+toid+"): " + boksName.get(toid) + ", level: " + level + "");
						continue;
					}
					
					swportidBack = (String)hmBack.get("swportid");
				}
				
				// N� kan vi markere at vlanet kj�rer ogs� p� linken tilbake
				String[] rVlanBack = {
					swportidBack,
					String.valueOf(vlanid),
					(setDirection)?"o":"u"
				};
				trunkVlan.add(rVlanBack);
				if (DEBUG_OUT) outl(pad+"--><b>[NON-TRUNK]</b> Link back running on non-trunk OK (<b>"+rVlanBack[0]+"</b>)");
			}
		}

		// Sjekk om vlanet er aktivt p� noen ikke-trunk porter; vi m� evt. legge til
		// de uten to_netboxid
		{
			Map map = (Map)activeVlan.get(boksid);
			if (map != null && map.containsKey(new Integer(vlan)) ) {
				isActiveVlan = true;
				// Create trunkVlan records for all ports
				for (Iterator it = ((Collection)map.get(new Integer(vlan))).iterator(); it.hasNext();) {
					String swportid = (String)it.next();
					String[] rVlan = {
						swportid,
						String.valueOf(vlanid),
						(setDirection)?"n":"u"
					};
					trunkVlan.add(rVlan);
				}
			}
		}

		// Sjekk om det er noen trunker p� denne enheten vlanet vi er p� har lov til � kj�re p�
		HashMap boksAllowedMap = (HashMap)allowedVlan.get(boksid);
		if (boksAllowedMap == null) {
			if (cameFromTrunk) {
				if (fromid == null) {
					// Dette er f�rste enhet, og da kan dette faktisk skje
					if (DEBUG_OUT) outl(pad+">ERROR! AllowedVlan not found for vlan: " + vlan + ", boksid("+boksid+"): " + boksName.get(boksid) + ", level: " + level + "");
				} else {
					if (DEBUG_OUT) outl(pad+"><font color=\"red\">ERROR! Should not happen, AllowedVlan not found for vlan: " + vlan + ", boksid("+boksid+"): " + boksName.get(boksid) + ", level: " + level + "</font>");
				}
			}
			if (DEBUG_OUT) outl(pad+"><font color=\"red\">[RETURN]</font> from node("+boksid+"): " + boksName.get(boksid) + ", isActiveVlan: <b>" + isActiveVlan+"</b>, no trunks to traverse.");
			// Return true hvis det er noen ikke-trunker som kj�rer p� boksen
			// Dette skal kun ha betydning hvis det er en ikke-trunk opp til gw'en
			return isActiveVlan;
		}
		boolean isActiveVlanTrunk = false;
		Iterator iter = boksAllowedMap.values().iterator();
		while (iter.hasNext()) {
			//HashMap hm = (HashMap)l.get(i);
			HashMap hm = (HashMap)iter.next();
			String hexstr = (String)hm.get("hexstring");
			String toid = (String)hm.get("to_netboxid");
			String swportid = (String)hm.get("swportid");
			String swportidBack;

			// Linken tilbake skal vi ikke f�lge uansett
			if (toid.equals(fromid)) continue;

			if (boksGwSet.contains(toid)) {
				/*
				if (foundGwUplinkSet.contains(toid)) {
					// Vi har allerede funnet uplink til gw p� en ikke-trunk, og da sier vi at vlanet ikke g�r over denne trunken
					continue;
				}
				*/
				if (swportGwVlanMap.containsKey(swportid+":"+vlan)) {
					if (!isAllowedVlan(hexstr, vlan)) {
						if (DEBUG_OUT) outl(pad+"--><font color=\"red\">ERROR, running on trunk to GW, but isAllowedVlan is false, vlan: <b>" + vlan + "</b>, boksid("+boksid+"): <b>" + boksName.get(boksid) + "</b>, to("+toid+"): <b>" + boksName.get(toid) + "</b> level: <b>" + level + "</b> (<b>"+swportid+"</b>)");
						continue;
					}

					// Dette er link til en GW, den blir da 'o' og vi skal ikke traversere
					String[] tvlan = {
						swportid,
						String.valueOf(vlanid),
						"o"
					};

					if (DEBUG_OUT) outl(pad+"--><b>[TRUNK-GW]</b> Running on trunk, vlan: <b>" + vlan + "</b>, boksid("+boksid+"): <b>" + boksName.get(boksid) + "</b>, to("+toid+"): <b>" + boksName.get(toid) + "</b> level: <b>" + level + "</b> (<b>"+tvlan[0]+"</b>)");
					trunkVlan.add(tvlan);
					isActiveVlanTrunk = true;
					foundGwports.add(swportGwVlanMap.get(swportid+":"+vlan));
				}
				continue;
			}

			// S� trenger vi recorden for linken tilbake
			{
				HashMap boksAllowedMapBack = (HashMap)allowedVlan.get(toid);
				if (boksAllowedMapBack == null) {
					if (DEBUG_OUT) outl(pad+">ERROR! AllowedVlan not found for vlan: " + vlan + ", toid("+toid+"): " + boksName.get(toid) + ", level: " + level + "");
					continue;
				}
				HashMap hmBack = (HashMap)boksAllowedMapBack.get(boksid);
				if (hmBack == null) {
					// Linken tilbake mangler
					if (DEBUG_OUT) outl(pad+"---->ERROR! Link back not found for vlan: " + vlan + ", toid("+toid+"): " + boksName.get(toid) + ", level: " + level + "");
					continue;
				}
				swportidBack = (String)hmBack.get("swportid");

				String hexstrBack = (String)hmBack.get("hexstring");
				if (hexstrBack == null) {
					// Linken tilbake mangler
					if (DEBUG_OUT) outl(pad+"---->ERROR! hexstring back not found for vlan: " + vlan + ", toid("+toid+"): " + boksName.get(toid) + ", level: " + level + "");
					continue;
				}
				if (hexstr == null) {
					// Linken tilbake mangler
					if (DEBUG_OUT) outl(pad+"---->ERROR! hexstring not found for vlan: " + vlan + ", toid("+toid+"): " + boksName.get(toid) + ", level: " + level + "");
					continue;
				}

				// Hvis en av dem ikke tillater dette vlanet � kj�re f�lger vi ikke denne linken
				if (!isAllowedVlan(hexstr, vlan) || !isAllowedVlan(hexstrBack, vlan)) {
					if (DEBUG_OUT) outl(pad+"----><b>NOT</b> allowed to("+toid+"): " + boksName.get(toid) + "");
					continue;
				}
			}

			if (DEBUG_OUT) outl(pad+"----><b>Allowed</b> to("+toid+"): " + boksName.get(toid) + ", visiting...");

			// Sjekk om linken er blokkert av spanning tree
			if (spanTreeBlocked.contains(swportid+":"+vlan) || spanTreeBlocked.contains(swportidBack+":"+vlan)) {
				// Jepp, da legger vi til vlanet med blokking i begge ender
				String[] tvlan = {
					swportid,
					String.valueOf(vlanid),
					"b"
				};
				String[] tvlanBack = {
					swportidBack,
					String.valueOf(vlanid),
					"b"
				};
				trunkVlan.add(tvlan);
				trunkVlan.add(tvlanBack);
				isActiveVlanTrunk = true;
				if (DEBUG_OUT) outl(pad+"------><font color=\"purple\">Link blocked by spanning tree, boksid("+boksid+"): <b>"+boksName.get(boksid)+"</b> toid:("+toid+"): <b>"+ boksName.get(toid) + "</b>, vlan: <b>" + vlan + "</b>, level: <b>" + level + "</b></font>");
				continue;
			}


			//if (DEBUG_OUT) outl(pad+"---->Visiting("+toid+"): " + boksName.get(toid) + "");

			// Brukes for � unng� dupes
			//visitNode.add(boksid);

			if (vlanTraverseLink(vlan, vlanid, boksid, toid, true, setDirection, nontrunkVlan, allowedVlan, activeVlan, swportidMap, spanTreeBlocked, trunkVlan, dataStructs, foundGwports, visitedNodeSet, level+1, DEBUG_OUT, boksGwSet, swportGwVlanMap, boksName)) {
				// Vi vet n� at vlanet kj�rer p� denne trunken
				String[] tvlan = {
					swportid,
					String.valueOf(vlanid),
					(setDirection)?"n":"u"
				};
				String[] tvlanBack = {
					swportidBack,
					String.valueOf(vlanid),
					(setDirection)?"o":"u"
				};
				trunkVlan.add(tvlan);
				trunkVlan.add(tvlanBack);
				isActiveVlanTrunk = true;
				if (DEBUG_OUT) outl(pad+"---->Returned active on trunk, vlan: <b>" + vlan + "</b>, boksid("+boksid+"): <b>" + boksName.get(boksid) + "</b>, to("+toid+"): <b>" + boksName.get(toid) + "</b> level: <b>" + level + "</b> (<b>"+tvlan[0]+" '"+tvlan[2]+"' / "+tvlanBack[0]+" '"+tvlanBack[2]+"'</b>)");
			} else {
				if (DEBUG_OUT) outl(pad+"---->Returned NOT active on trunk, vlan: <b>" + vlan + "</b>, boksid("+boksid+"): <b>" + boksName.get(boksid) + "</b>, to("+toid+"): <b>" + boksName.get(toid) + "</b> level: <b>" + level + "</b>");
			}
			//visitNode.remove(boksid);


		}


		// Vi skal returnere om vlanet kj�rer p� denne boksen
		// F�rst sjekker vi om noen av trunkene har dette vlanet aktivt
		if (isActiveVlanTrunk) {
			if (DEBUG_OUT) outl(pad+"><font color=\"red\">[RETURN]</font> from node("+boksid+"): " + boksName.get(boksid) + ", <b>ActiveVlan on trunk</b>");
			return true;
		}

		// Nei, da sjekker vi om det er noen ikke-trunker som har det aktivt
		if (isActiveVlan) {
			if (DEBUG_OUT) outl(pad+"><font color=\"red\">[RETURN]</font> from node("+boksid+"): " + boksName.get(boksid) + ", <b>ActiveVlan on NON-trunk</b>");
			return true;
		}

		/*
		HashSet hs = (HashSet)activeVlan.get(boksid);
		if (hs != null && hs.contains(new Integer(vlan)) ) {
			if (DEBUG_OUT) outl(pad+"><font color=\"red\">[RETURN]</font> from node("+boksid+"): " + boksName.get(boksid) + ", <b>ActiveVlan on NON-trunk</b>");
			return true;
		}
		*/
		if (DEBUG_OUT) outl(pad+"><font color=\"red\">[RETURN]</font> from node("+boksid+"): " + boksName.get(boksid) + ", <b>Not active</b>");
		return false;
	}

	private static boolean isAllowedVlan(String hexstr, int vlan)
	{
		hexstr = hexstr.replaceAll(":", "");
		if (hexstr.length() == 256 || hexstr.length() == 254) {
			return isAllowedVlanFwd(hexstr, vlan);
		}
		return isAllowedVlanRev(hexstr, vlan);
	}

	private static boolean isAllowedVlanFwd(String hexstr, int vlan)
	{
		if (vlan < 0 || vlan > 1023) return false;
		int index = vlan / 4;

		int allowed = Integer.parseInt(String.valueOf(hexstr.charAt(index)), 16);
		return ((allowed & (1<<3-(vlan%4))) != 0);
	}

	private static boolean isAllowedVlanRev(String hexstr, int vlan)
	{
		if (vlan < 0 || vlan > 1023) return false;
		int index = hexstr.length() - (vlan / 4 + 1);
		if (index < 0) return false;

		int allowed = Integer.parseInt(String.valueOf(hexstr.charAt(index)), 16);
		return ((allowed & (1<<(vlan%4))) != 0);
	}



	private void outl(String s)
	{
		System.out.println(s);
	}
	private void out(String s)
	{
		System.out.print(s);
	}

	private void err(String s) { System.err.print(s); }
	private void errl(String s) { System.err.println(s); }
}
