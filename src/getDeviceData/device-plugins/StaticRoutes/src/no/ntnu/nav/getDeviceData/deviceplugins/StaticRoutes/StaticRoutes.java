package no.ntnu.nav.getDeviceData.deviceplugins.StaticRoutes;

import java.util.*;
import java.util.regex.*;

import no.ntnu.nav.logger.*;
import no.ntnu.nav.SimpleSnmp.*;
import no.ntnu.nav.ConfigParser.*;
import no.ntnu.nav.util.*;
import no.ntnu.nav.getDeviceData.Netbox;
import no.ntnu.nav.getDeviceData.deviceplugins.*;
import no.ntnu.nav.getDeviceData.dataplugins.*;
import no.ntnu.nav.getDeviceData.dataplugins.Module.*;
import no.ntnu.nav.getDeviceData.dataplugins.Gwport.*;
import no.ntnu.nav.getDeviceData.dataplugins.Swport.*;

/**
 * <p>
 * Device plugin for collecting static routes from routers.
 * </p>
 *
 * <p>
 * This plugin handles the following OID keys:
 * </p>
 *
 * <p>
 * <ui>
 *  <li>ipRouteDest</li>
 *  <li>ipRouteMask</li>
 *  <li>ipRouteNextHop</li>
 *  <li>ipRouteType</li>
 *  <li>ipRouteProto</li>
 * </ul>
 * </p>
 */

public class StaticRoutes implements DeviceHandler
{
	private static String[] canHandleOids = {
		"ipRouteDest",
		"ipRouteMask",
		"ipRouteNextHop",
		"ipRouteType",
		"ipRouteProto",
	};

	private static String[] supportedCatids = {
		"GSW",
		"GW",
	};

	private SimpleSnmp sSnmp;

	public int canHandleDevice(Netbox nb) {
		if (!new HashSet(Arrays.asList(supportedCatids)).contains(nb.getCat())) return NEVER_HANDLE;
		int v = nb.isSupportedAllOids(canHandleOids) ? ALWAYS_HANDLE : NEVER_HANDLE;
		Log.d("SRT_CANHANDLE", "CHECK_CAN_HANDLE", "Can handle device: " + v);
		return v;
	}

	public void handleDevice(Netbox nb, SimpleSnmp sSnmp, ConfigParser cp, DataContainers containers) throws TimeoutException
	{
		Log.setDefaultSubsystem("SRT_DEVHANDLER");

		ModuleContainer mc;
		{
			DataContainer dc = containers.getContainer("ModuleContainer");
			if (dc == null) {
				Log.w("NO_CONTAINER", "No ModuleContainer found, plugin may not be loaded");
				return;
			}
			if (!(dc instanceof ModuleContainer)) {
				Log.w("NO_CONTAINER", "Container is not a ModuleContainer! " + dc);
				return;
			}
			mc = (ModuleContainer)dc;
		}
		
		GwportContainer gwc;
		{
			DataContainer dc = containers.getContainer("GwportContainer");
			if (dc == null) {
				Log.w("NO_CONTAINER", "No GwportContainer found, plugin may not be loaded");
				return;
			}
			if (!(dc instanceof GwportContainer)) {
				Log.w("NO_CONTAINER", "Container is not a GwportContainer! " + dc);
				return;
			}
			gwc = (GwportContainer)dc;
		}

		SwportContainer sc;
		{
			DataContainer dc = containers.getContainer("SwportContainer");
			if (dc == null) {
				Log.w("NO_CONTAINER", "No SwportContainer found, plugin may not be loaded");
				return;
			}
			if (!(dc instanceof SwportContainer)) {
				Log.w("NO_CONTAINER", "Container is not an SwportContainer! " + dc);
				return;
			}
			sc = (SwportContainer)dc;
		}


		String netboxid = nb.getNetboxidS();
		String ip = nb.getIp();
		String cs_ro = nb.getCommunityRo();
		String type = nb.getType();
		String sysName = nb.getSysname();
		String cat = nb.getCat();
		this.sSnmp = sSnmp;

		boolean fetch = processCiscoGw(nb, netboxid, ip, cs_ro, type, mc, gwc, sc);
			
		// Commit data
		if (fetch) {
			gwc.commit();
		}
	}

	/*
	 * CiscoGw
	 *
	 */
	private boolean processCiscoGw(Netbox nb, String netboxid, String ip, String cs_ro, String type, ModuleContainer mc, GwportContainer gwc, SwportContainer sc) throws TimeoutException {

		/*

o For hver ruter (GW/GSW)

   o Plukk ut alle ruter der
     ipRouteType = indirect(4) & ipRouteProto = local(2)

     o Av disse UNNLAT ruter der:
       - ipRouteDest = '0.0.0.0' (default ruta fra en kantruter)
       - ipRouteNextHop = 'Null0' (tror de utelates i utgangspunktet)
       - Dersom ipRouteDest/ipRouteMask (alts� prefixet) finnes fra f�r,
         da med en nettype som er dynamisk, alts� en som har
         nettype.edit='f'
         (dette kan bl.a. inntreffe ved "flytende statiske ruter", slik
          ntnu fra f.eks. sb-gsw mot erke-gw)
       - Dersom masken er veldig grov, dvs mask <=16
         (b�r ikke opptre, men dersom man ikke kj�rer classless ruting)
       - Man kan vurdere � unnlate mask=32, alts� hostruter, ta de med
         i f�rste runde. Tror ikke de kompliserer.

     o For rutene man da har igjen:
       - plukk ut ipRouteDest, ipRouteMask, ipRouteNextHop
       - lag ny/oppdater prefix og vlan-post som beskrevet over.

   o Motsatt m� du ha logikk for � slette statiske ruter som er fjernet
     fra ruteren.

		*/

		// Retain ipRouteType = indirect(4) & ipRouteProto = local(2)
		MultiMap routeType = util.reverse(sSnmp.getAllMap(nb.getOid("ipRouteType")));
		Set routes = routeType.get("4");
	  //System.err.println("Routes1: " + routes);
		if (routes.isEmpty()) return false;

		MultiMap routeProto = util.reverse(sSnmp.getAllMap(nb.getOid("ipRouteProto")));
	  //System.err.println("Routes2: " + routes);
		routes.retainAll(routeProto.get("2"));
		if (routes.isEmpty()) return false;

		// Remove routeDest = 0.0.0.0 and ipRouteNextHop = Null0
		Map routeDest = sSnmp.getAllMap(nb.getOid("ipRouteDest"));
		MultiMap routeDestMM = util.reverse(routeDest);
	  //System.err.println("Routes3: " + routes);
		routes.removeAll(routeDestMM.get("0.0.0.0"));
		if (routes.isEmpty()) return false;

		Map routeNextHop = sSnmp.getAllMap(nb.getOid("ipRouteNextHop"));
		MultiMap routeNextHopMM = util.reverse(routeNextHop);
	  //System.err.println("Routes4: " + routes);
		routes.removeAll(routeNextHopMM.get("Null0"));
	  //System.err.println("Routes5: " + routes);
		if (routes.isEmpty()) return false;
	  //System.err.println("Routes6: " + routes);

		Map routeMask = sSnmp.getAllMap(nb.getOid("ipRouteMask"));

		// Create net map
		List gwipList = sSnmp.getAll(nb.getOid("ipAdEntIfIndex"));
		Map netmaskMap = sSnmp.getAllMap(nb.getOid("ipAdEntIfNetMask"));
		Set netmaskSet = new HashSet();
		Map netMap = new HashMap();
		for (Iterator it = gwipList.iterator(); it.hasNext();) {
			String[] s = (String[])it.next();
			String gwip = Prefix.hexToIp(s[0]);
			String ifindex = s[1];
			String mask = Prefix.hexToIp((String)netmaskMap.get(gwip));
			netmaskSet.add(mask);
			String net = Prefix.and_ip(gwip, mask);
			netMap.put(net, ifindex);
		}

		Map ifDescr = sSnmp.getAllMap(nb.getOid("ifDescr"), true);
		Map ifAlias = sSnmp.getAllMap(nb.getOid("ifAlias"), true);
		Map admStatusMap = sSnmp.getAllMap(nb.getOid("ifAdminStatus"));
		Map speedMap = sSnmp.getAllMap(nb.getOid("ifSpeed"));

		for (Iterator it = routes.iterator(); it.hasNext();) {
			String r = Prefix.hexToIp((String)it.next());
			String alias = (String)ifAlias.get(r);
			String dest = Prefix.hexToIp((String)routeDest.get(r));
			String nexthop = Prefix.hexToIp((String)routeNextHop.get(r));
			String mask = Prefix.hexToIp((String)routeMask.get(r));
			String ifindex = null;
			// Try to find ifindex by searching all local interfaces
			for (Iterator maskIt = netmaskSet.iterator(); maskIt.hasNext();) {
				String m = (String)maskIt.next();
				String net = Prefix.and_ip(nexthop, m);
				if (netMap.containsKey(net)) {
					ifindex = (String)netMap.get(Prefix.and_ip(nexthop, m));
					break;
				}
			}
			if (ifindex == null) {
				Log.w("PROCESS_SRT", "Cannot find ifindex for route " + r + " (nexthop: " + nexthop + " mask: " + mask + " net: " + Prefix.and_ip(nexthop, mask) + "), skipping");
				continue;
			}
			if (Prefix.masklen(mask) <= 16) {
				Log.w("PROCESS_SRT", "Mask is <=16 ("+Prefix.masklen(mask)+") for route " + r + ", ifindex " + ifindex);
				continue;
			}

			//Log.d("PROCESS_SRT", "Check static route " + dest+"/"+mask + ", " + nexthop + ", ifindex " + ifindex);
			//System.err.println("Check static route " + dest+"/"+mask + ", " + nexthop + ", ifindex " + ifindex);

			// Ignore any admDown interfaces
			String link = (String)admStatusMap.get(ifindex);
			//System.err.println("  Link: " + link);
			if (!"1".equals(link)) continue;

			String interf = (String)ifDescr.get(ifindex);
			//System.err.println("  interf: " + interf);
			if (interf == null || interf.startsWith("EOBC") || interf.equals("Vlan0")) continue;

			// Determine and create the module
			int module = 1;
			String modulePattern = ".*?(\\d+)/.*";
			if (interf.matches(modulePattern)) {
				Matcher m = Pattern.compile(modulePattern).matcher(interf);
				m.matches();
				module = Integer.parseInt(m.group(1));
			} else {
				boolean sup = false;
				for (Iterator modIt = mc.getModules(); modIt.hasNext();) {
					Module mod = (Module)modIt.next();
					String modDescr = mod.getDescr();
					if (modDescr != null && modDescr.toLowerCase().indexOf("supervisor") >= 0) {
						module = mod.getModule();
						sup = true;
						break;
					}
				}
				if (!sup) {
					Log.w("SRT_MATCH-MODULE", "Supervisor not found and could not match module pattern to if: " + interf);
				}
				if (mc.getModule(module) == null && mc.getModule(0) != null) {
					Log.w("SRT_MATCH-MODULE", "No module match from interf, defaulting to module 0");
					module = 0;
				}
			}
			if (mc.getModule(module) == null) {
				// Not allowed to create module
				Log.w("SRT_MATCH-MODULE", "Module " + module + " does not exist on netbox " + nb.getSysname() + ", skipping");
				//System.err.println("Module " + module + " does not exist on netbox " + nb.getSysname() + ", skipping");
				continue;
			}
			GwModule gwm = gwc.gwModuleFactory(module);
			//System.err.println("  Route ok, module: " + module);
		
			// Create Vlan
			// netident = 'sysname-til-ruteren-du-sp�r,ipRouteNextHop'
			String netident = nb.getSysname()+","+nexthop;
			Vlan vl = gwm.vlanFactory(netident);
			vl.setNettype("static");
			vl.setDescription(alias);

			// Create Gwport
			Gwport gwp = gwm.gwportFactory(ifindex, (String)ifDescr.get(ifindex));

			// We can now ignore this ifindex as an swport
			sc.ignoreSwport(ifindex);

			// Set speed from Mib-II
			double speed = speedMap.containsKey(ifindex) ? Long.parseLong((String)speedMap.get(ifindex)) / 1000000.0 : 0.0;
			gwp.setSpeed(speed);

			// Create prefix
			Prefix p = gwp.prefixFactory(dest, false, mask, vl);

			Log.d("PROCESS_SRT", "Added static route " + dest+"/"+mask + ", module " + module + ", ifindex " + ifindex);

			
		}
		return true;
	}

	private static boolean isNumber(String s) {
		try {
			Integer.parseInt(s);
		} catch (NumberFormatException e) {
			return false;
		}
		return true;
	}

}
