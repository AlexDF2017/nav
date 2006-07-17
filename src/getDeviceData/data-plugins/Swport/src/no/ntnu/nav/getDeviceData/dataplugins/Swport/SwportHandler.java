/*
 * $Id$
 *
 * Copyright 2003-2005 Norwegian University of Science and Technology
 * 
 * This file is part of Network Administration Visualized (NAV)
 * 
 * NAV is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 * 
 * NAV is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with NAV; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 *
 *
 * Authors: Kristian Eide <kreide@gmail.com>
 * 
 */

package no.ntnu.nav.getDeviceData.dataplugins.Swport;

import java.util.*;
import java.sql.*;

import no.ntnu.nav.logger.*;
import no.ntnu.nav.util.*;
import no.ntnu.nav.Database.*;
import no.ntnu.nav.getDeviceData.Netbox;
import no.ntnu.nav.getDeviceData.dataplugins.*;
import no.ntnu.nav.getDeviceData.dataplugins.Module.ModuleHandler;

/**
 * DataHandler plugin for getDeviceData; provides an interface for storing
 * switch data, which includes modules and switch ports.
 *
 * @see SwportContainer
 */

public class SwportHandler implements DataHandler {

	/*
	private static Map moduleMap;
	private static Map swportMap;
	private static Map portMap;
	*/

	/**
	 * Fetch initial data from swport table.
	 */
	public synchronized void init(Map persistentStorage, Map changedDeviceids) {
		if (persistentStorage.containsKey("initDone")) return;
		persistentStorage.put("initDone", null);

		/*
		Map m;
		Map swpMap;
		ResultSet rs;
		long dumpBeginTime,dumpUsedTime;

		Log.setDefaultSubsystem("SwportHandler");

		try {
		
			// module, swport
			dumpBeginTime = System.currentTimeMillis();
			m = Collections.synchronizedMap(new HashMap());
			swpMap = Collections.synchronizedMap(new HashMap());
			Map portMapL = Collections.synchronizedMap(new HashMap());
			rs = Database.query("SELECT deviceid,serial,hw_ver,fw_ver,sw_ver,moduleid,module,netboxid,model,descr,up,swport.swportid,ifindex,port,interface,link,speed,duplex,media,trunk,portname,vlan,hexstring FROM device JOIN module USING (deviceid) LEFT JOIN swport USING (moduleid) LEFT JOIN swportallowedvlan USING (swportid) ORDER BY moduleid");
			while (rs.next()) {
				SwModule md = new SwModule(rs.getString("serial"), rs.getString("hw_ver"), rs.getString("fw_ver"), rs.getString("sw_ver"), rs.getInt("module"), null);
				md.setDeviceid(rs.getInt("deviceid"));
				md.setModuleid(rs.getInt("moduleid"));
				md.setModel(rs.getString("model"));
				md.setDescr(rs.getString("descr"));

				int moduleid = rs.getInt("moduleid");
				if (rs.getString("ifindex") != null && rs.getString("ifindex").length() > 0) {
					do {
						if (rs.getString("port") != null) {
							String portKey = rs.getString("moduleid")+":"+rs.getString("port");
							if (portMapL.containsKey(portKey)) {
								System.err.println("ERROR! Dup port: " + portKey);
								Database.update("DELETE FROM swport WHERE swportid='"+rs.getString("swportid")+"'");
								continue;
							} else {
								portMapL.put(portKey, rs.getString("swportid"));
							}
						}

						Swport sd = new Swport(rs.getString("ifindex"));
						sd.setSwportid(rs.getInt("swportid"));
						
						if (rs.getString("port") != null) sd.setPort(new Integer(rs.getInt("port")));
						if (rs.getString("link") != null) sd.setLink(rs.getString("link").charAt(0));
						sd.setSpeed(rs.getString("speed"));
						if (rs.getString("duplex") != null) sd.setDuplex(rs.getString("duplex").charAt(0));
						sd.setMedia(rs.getString("media"));
						sd.setPortname(rs.getString("portname"));
						sd.setInterface(rs.getString("interface"));
						if (rs.getString("vlan") != null) sd.setVlan(rs.getInt("vlan"));
						if (rs.getString("trunk") != null) sd.setTrunk(rs.getBoolean("trunk"));
						sd.setHexstring(rs.getString("hexstring"));

						md.addSwport(sd);
						//String key = rs.getString("netboxid")+":"+rs.getString("ifindex");
						String key = rs.getString("moduleid")+":"+rs.getString("ifindex");
						if (swpMap.containsKey(key)) {
							System.err.println("ERROR! Non-unique ifindex, deleting...");
							Database.update("DELETE FROM swport WHERE swportid="+rs.getString("swportid"));
						} else {
							swpMap.put(key, md);
						}
					} while (rs.next() && rs.getInt("moduleid") == moduleid);
					rs.previous();
				}
			}
			swportMap = swpMap;
			portMap = portMapL;
			dumpUsedTime = System.currentTimeMillis() - dumpBeginTime;
			Log.d("INIT", "Dumped swport in " + dumpUsedTime + " ms");

		} catch (SQLException e) {
			Log.e("INIT", "SQLException: " + e.getMessage());
			e.printStackTrace(System.err);
		}
		*/

	}

	/**
	 * Return a DataContainer object used to return data to this
	 * DataHandler.
	 */
	public DataContainer dataContainerFactory() {
		return new SwportContainer(this);
	}
	
	/**
	 * Store the data in the DataContainer in the database.
	 */
	public void handleData(Netbox nb, DataContainer dc, Map changedDeviceids) {
		if (!(dc instanceof SwportContainer)) return;
		SwportContainer sc = (SwportContainer)dc;
		if (!sc.isCommited()) return;

		// Assign any module-less swports to module 1
		sc.assignSwportsWithoutModule();

		// Let ModuleHandler update the module table first
		ModuleHandler mh = new ModuleHandler();
		mh.handleData(nb, dc, changedDeviceids);

		Log.setDefaultSubsystem("SwportHandler");
		int newcnt = 0, updcnt = 0;

		try {
			Set moduleids = new HashSet();
			for (Iterator swModules = sc.getSwModules(); swModules.hasNext();) {
				SwModule md = (SwModule)swModules.next();
				String moduleid = md.getModuleidS();
				if ("0".equals(moduleid)) {
					System.err.println("Moduleid is null!! " + md);
					continue;
				}
				moduleids.add(moduleid);
			}
			if (moduleids.isEmpty()) {
				Log.d("UPDATE_SWPORT", "No modules found for " + nb.getSysname());
				return;
			}
			String[] moduleidA = util.stringArray(moduleids);

			Map moduleMap = new HashMap();
			ResultSet rs = Database.query("SELECT swportid,moduleid,ifindex,port,interface,link,speed,duplex,media,trunk,portname,vlan,hexstring FROM swport LEFT JOIN swportallowedvlan USING (swportid) WHERE moduleid IN ("+ util.join(moduleidA, ",") +")");
			Map swportMap = new HashMap();
			Map portModuleMap = new HashMap();
			while (rs.next()) {
				Map portMap;
				String moduleid = rs.getString("moduleid");
				if ( (portMap=(Map)portModuleMap.get(moduleid)) == null) portModuleMap.put(moduleid, portMap = new HashMap());

				String ifindex = rs.getString("ifindex");
				if (swportMap.containsKey(ifindex)) {
					// Delete old ifindex
					Log.d("DEL_DUP_IFINDEX", "Deleting duplicate ifindex " + ifindex + " on " + nb.getSysname());
					Database.update("DELETE FROM swport WHERE swportid="+rs.getInt("swportid"));
					continue;
				}

				if (rs.getString("port") != null) {
					Integer port = new Integer(rs.getInt("port"));
					if (portMap.containsKey(port)) {
						Log.d("DEL_DUP_PORT", "Deleting duplicate port " + port + " on moduleid " + rs.getString("moduleid") + ", " + nb.getSysname());
						Database.update("DELETE FROM swport WHERE swportid = '"+rs.getString("swportid")+"'");
						continue;
					} else {
						portMap.put(port, rs.getString("swportid"));
					}
				}

				Swport sd = new Swport(ifindex);
				sd.setSwportid(rs.getInt("swportid"));
				sd.setPort(new Integer(rs.getInt("port")));

				if (rs.getString("link") != null) sd.setLink(rs.getString("link").charAt(0));
				sd.setSpeed(rs.getString("speed"));
				if (rs.getString("duplex") != null) sd.setDuplex(rs.getString("duplex").charAt(0));
				sd.setMedia(rs.getString("media"));
				sd.setPortname(rs.getString("portname"));
				sd.setInterface(rs.getString("interface"));
				if (rs.getString("vlan") != null) sd.setVlan(rs.getInt("vlan"));
				if (rs.getString("trunk") != null) sd.setTrunk(rs.getBoolean("trunk"));
				sd.setHexstring(rs.getString("hexstring"));

				swportMap.put(ifindex, sd);
			}

			for (Iterator swModules = sc.getSwModules(); swModules.hasNext();) {
				SwModule md = (SwModule)swModules.next();
				String moduleid = md.getModuleidS();
				Map portMap = (Map) portModuleMap.get(moduleid);
				// This can happen for new modules
				if (portMap == null) portMap = new HashMap();

				//System.err.println("Module: " + md);

				// Så alle swportene
				String swportid;
				for (Iterator j = md.getSwports(); j.hasNext();) {
					Swport sd = (Swport)j.next();

					//System.err.println(" Swport: " + sd + " ("+sc.getIgnoreSwport(sd.getIfindex())+")");

					// Check if this swport should be ignored
					if (sc.getIgnoreSwport(sd.getIfindex())) continue;

					Swport oldsd = (Swport)swportMap.get(sd.getIfindex());

					// If there is an identical port, delete it
					if (sd.getPort() != null && portMap.containsKey(sd.getPort())) {
						if (oldsd == null || (!oldsd.getSwportidS().equals(portMap.get(sd.getPort())))) {
							System.err.println("Want to delete port: " + moduleid +  ", " + sd.getPort() + ", " + nb);
							Log.d("DEL_DUP_PORT", "Deleting old duplicate port " + sd.getPort() + " on module " + moduleid);
							Database.update("DELETE FROM swport WHERE swportid = '"+portMap.get(sd.getPort())+"'");
						}
					}

					if (oldsd == null) {

						// Sett inn ny
						rs = Database.query("SELECT nextval('swport_swportid_seq') AS swportid");
						rs.next();
						swportid = rs.getString("swportid");

						Log.d("NEW_SWPORT", "New swport, swportid="+swportid+", moduleid="+moduleid+", port="+sd.getPort()+", ifindex="+sd.getIfindex()+", link="+sd.getLink()+", speed="+sd.getSpeed()+", duplex="+sd.getDuplexS()+", media="+Database.addSlashes(sd.getMedia())+", vlan="+sd.getVlanS()+", trunk="+sd.getTrunkS()+", portname="+Database.addSlashes(sd.getPortname()));

						String[] inss = {
							"swportid", swportid,
							"moduleid", moduleid,
							"port", sd.getPortS(),
							"ifindex", sd.getIfindex(),
							"interface", Database.addSlashes(sd.getInterface()),
							"link", sd.getLinkS(),
							"speed", sd.getSpeed(),
							"Duplex", sd.getDuplexS(),
							"media", Database.addSlashes(sd.getMedia()),
							"vlan", sd.getVlanS(),
							"trunk", sd.getTrunkS(),
							"portname", Database.addSlashes(sd.getPortname())
						};
						Database.insert("swport", inss);
						//changedDeviceids.put(md.getDeviceidS(), new Integer(DataHandler.DEVICE_ADDED));
						newcnt++;

					} else {
						swportid = oldsd.getSwportidS();
						if (!sd.equalsSwport(oldsd)) {
							// Vi må oppdatere
							Log.d("UPDATE_SWPORT", "Update swportid: "+swportid+" ifindex="+sd.getIfindex());
							Log.d("UPDATE_SWPORT", "Old: " + oldsd + ", New: " + sd);

							String[] set = {
								"moduleid", moduleid,
								"port", sd.getPortS(),
								"interface", Database.addSlashes(sd.getInterface()),
								"link", sd.getLinkS(),
								"speed", sd.getSpeed(),
								"duplex", sd.getDuplexS(),
								"media", Database.addSlashes(sd.getMedia()),
								"vlan", sd.getVlanS(),
								"trunk", sd.getTrunkS(),
								"portname", Database.addSlashes(sd.getPortname())
							};
							String[] where = {
								"swportid", swportid
							};
							Database.update("swport", set, where);
							//changedDeviceids.put(md.getDeviceidS(), new Integer(DataHandler.DEVICE_UPDATED));
							updcnt++;

							/*
							String oldPortKey = oldmd.getModuleid()+":"+oldsd.getPort();
							String portKey = moduleid+":"+sd.getPort();
							if (sd.getPort() != null) {
								portMap.remove(oldPortKey);
								portMap.put(portKey, swportid);
							}
							*/
						}
					}
					sd.setSwportid(swportid);
					if (sd.getPort() != null) portMap.put(sd.getPort(), swportid);

					sd.setRetEmptyHexstring(true);
					if (sd.getTrunk() != null && !sd.getTrunk().booleanValue()) {
						// Slett evt. fra swportallowedvlan
						if (oldsd != null && oldsd.getHexstring() != null && oldsd.getHexstring().length() > 0) {
							Database.update("DELETE FROM swportallowedvlan WHERE swportid='"+sd.getSwportid()+"'");
						}

					} else if (sd.getTrunk() != null) {
						// Trunk, da må vi evt. oppdatere swportallowedvlan
						if (sd.getHexstring().length() > 0) {
							if (oldsd == null || oldsd.getHexstring() == null || oldsd.getHexstring().length() == 0) {
								Database.update("INSERT INTO swportallowedvlan (swportid,hexstring) VALUES ('"+sd.getSwportid()+"','"+Database.addSlashes(sd.getHexstring())+"')");
							} else if (!sd.getHexstring().equals(oldsd.getHexstring())) {
								Database.update("UPDATE swportallowedvlan SET hexstring = '"+Database.addSlashes(sd.getHexstring())+"' WHERE swportid = '"+sd.getSwportid()+"'");
							}
						}
					}

				}

			}

		} catch (SQLException e) {
			Log.e("HANDLE", "SQLException: " + e.getMessage());
			e.printStackTrace(System.err);
		}

		if (newcnt > 0 || updcnt > 0) {
			Log.i("HANDLE", nb.getSysname() + ": New: " + newcnt + ", Updated: " + updcnt);
		}

	}

}
