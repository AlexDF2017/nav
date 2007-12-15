/*
=============================================
        manage
    SQL Initialization script for NAV's
    manage database.  Read the README file
    for more info.
    
    Run the command:
    psql manage -f manage.sql
    
	!! WARNING !!

	This SQL script is encoded as unicode (UTF-8), before you do make
	changes and commit, be 100% sure that your editor does not mess it up.
    
    Check 1 : These norwegian letters looks nice:
    ! æøåÆØÅ !
    Check 2 : This is the Euro currency sign: 
    ! € !
=============================================
*/

-- This table has possibly gone unused since NAV 2
CREATE TABLE status (
  statusid SERIAL PRIMARY KEY,
  trapsource VARCHAR NOT NULL,
  trap VARCHAR NOT NULL,
  trapdescr VARCHAR,
  tilstandsfull CHAR(1) CHECK (tilstandsfull='Y' OR tilstandsfull='N') NOT NULL,
  boksid INT2,
  fra TIMESTAMP NOT NULL,
  til TIMESTAMP
);

CREATE TABLE org (
  orgid VARCHAR(30) PRIMARY KEY,
  parent VARCHAR(30) REFERENCES org (orgid),
  descr VARCHAR,
  opt1 VARCHAR,
  opt2 VARCHAR,
  opt3 VARCHAR
);


CREATE TABLE usage (
  usageid VARCHAR(30) PRIMARY KEY,
  descr VARCHAR NOT NULL
);


CREATE TABLE location (
  locationid VARCHAR(30) PRIMARY KEY,
  descr VARCHAR NOT NULL
);

CREATE TABLE room (
  roomid VARCHAR(30) PRIMARY KEY,
  locationid VARCHAR(30) REFERENCES location,
  descr VARCHAR,
  opt1 VARCHAR,
  opt2 VARCHAR,
  opt3 VARCHAR,
  opt4 VARCHAR
);

CREATE TABLE nettype (
  nettypeid VARCHAR PRIMARY KEY,
  descr VARCHAR,
  edit BOOLEAN DEFAULT FALSE
);
INSERT INTO nettype (nettypeid,descr,edit) VALUES ('core','core',FALSE);
INSERT INTO nettype (nettypeid,descr,edit) VALUES ('dummy','dummy',FALSE);
INSERT INTO nettype (nettypeid,descr,edit) VALUES ('elink','elink',FALSE);
INSERT INTO nettype (nettypeid,descr,edit) VALUES ('lan','lan',FALSE);
INSERT INTO nettype (nettypeid,descr,edit) VALUES ('link','link',FALSE);
INSERT INTO nettype (nettypeid,descr,edit) VALUES ('loopback','loopbcak',FALSE);
INSERT INTO nettype (nettypeid,descr,edit) VALUES ('reserved','reserved',TRUE);
INSERT INTO nettype (nettypeid,descr,edit) VALUES ('private','private',FALSE);
INSERT INTO nettype (nettypeid,descr,edit) VALUES ('scope','scope',TRUE);
INSERT INTO nettype (nettypeid,descr,edit) VALUES ('static','static',FALSE);
INSERT INTO nettype (nettypeid,descr,edit) VALUES ('unknown','unknow',FALSE);

CREATE TABLE vlan (
  vlanid SERIAL PRIMARY KEY,
  vlan INT4,
  nettype VARCHAR NOT NULL REFERENCES nettype(nettypeid) ON UPDATE CASCADE ON DELETE CASCADE,
  orgid VARCHAR(30) REFERENCES org,
  usageid VARCHAR(30) REFERENCES usage,
  netident VARCHAR,
  description VARCHAR
);  
CREATE INDEX vlan_vlan_btree ON vlan USING btree (vlan);

CREATE TABLE prefix (
  prefixid SERIAL PRIMARY KEY,
  netaddr CIDR NOT NULL,
  vlanid INT4 REFERENCES vlan ON UPDATE CASCADE ON DELETE CASCADE,
  UNIQUE(netaddr)
);
CREATE INDEX prefix_vlanid_btree ON prefix USING btree (vlanid);

CREATE TABLE vendor (
  vendorid VARCHAR(15) PRIMARY KEY
);

CREATE TABLE cat (
  catid VARCHAR(8) PRIMARY KEY,
  descr VARCHAR,
  req_snmp BOOLEAN NOT NULL
);

INSERT INTO cat values ('GW','Routers (layer 3 device)','t');
INSERT INTO cat values ('GSW','A layer 2 and layer 3 device','t');
INSERT INTO cat values ('SW','Core switches (layer 2), typically with many vlans','t');
INSERT INTO cat values ('EDGE','Edge switch without vlans (layer 2)','t');
INSERT INTO cat values ('WLAN','Wireless equipment','t');
INSERT INTO cat values ('SRV','Server','f');
INSERT INTO cat values ('OTHER','Other equipment','f');

CREATE TABLE product (
  productid SERIAL PRIMARY KEY,
  vendorid VARCHAR(15) NOT NULL REFERENCES vendor ON UPDATE CASCADE ON DELETE CASCADE,
  productno VARCHAR NOT NULL,
  descr VARCHAR,
  UNIQUE (vendorid,productno)
);

CREATE TABLE deviceorder (
  deviceorderid SERIAL PRIMARY KEY,
  registered TIMESTAMP NOT NULL DEFAULT now(),
  ordered DATE,
  arrived TIMESTAMP DEFAULT 'infinity',
  ordernumber VARCHAR,
  comment VARCHAR,
  retailer VARCHAR,
  username VARCHAR,
  orgid VARCHAR(30) REFERENCES org (orgid) ON UPDATE CASCADE ON DELETE SET NULL,
  productid INTEGER REFERENCES product (productid) ON UPDATE CASCADE ON DELETE SET NULL,
  updatedby VARCHAR,
  lastupdated DATE);


CREATE TABLE device (
  deviceid SERIAL PRIMARY KEY,
  productid INT4 REFERENCES product ON UPDATE CASCADE ON DELETE SET NULL,
  serial VARCHAR,
  hw_ver VARCHAR,
  fw_ver VARCHAR,
  sw_ver VARCHAR,
	auto BOOLEAN NOT NULL DEFAULT false,
  active BOOLEAN NOT NULL DEFAULT false,
  deviceorderid INT4 REFERENCES deviceorder (deviceorderid) ON DELETE CASCADE,
  discovered TIMESTAMP NULL DEFAULT NOW(),
  UNIQUE(serial)
);

CREATE TABLE type (
  typeid SERIAL PRIMARY KEY,
  vendorid VARCHAR(15) NOT NULL REFERENCES vendor ON UPDATE CASCADE ON DELETE CASCADE,
  typename VARCHAR NOT NULL,
  sysObjectID VARCHAR NOT NULL,
  cdp BOOL DEFAULT false,
  tftp BOOL DEFAULT false,
  cs_at_vlan BOOL,
  chassis BOOL NOT NULL DEFAULT true,
  frequency INT4,
  descr VARCHAR,
  UNIQUE (vendorid, typename),
  UNIQUE (sysObjectID)
);

CREATE TABLE snmpoid (
  snmpoidid SERIAL PRIMARY KEY,
  oidkey VARCHAR NOT NULL,
  snmpoid VARCHAR NOT NULL,
  oidsource VARCHAR,
  getnext BOOLEAN NOT NULL DEFAULT true,
  decodehex BOOLEAN NOT NULL DEFAULT false,
  match_regex VARCHAR,
  defaultfreq INT4 NOT NULL DEFAULT 21600,
  uptodate BOOLEAN NOT NULL DEFAULT false,
  descr VARCHAR,
  oidname VARCHAR,
  mib VARCHAR,
  UNIQUE(oidkey)
);

CREATE TABLE netbox (
  netboxid SERIAL PRIMARY KEY,
  ip INET NOT NULL,
  roomid VARCHAR(30) NOT NULL CONSTRAINT netbox_room_fkey REFERENCES room ON UPDATE CASCADE,
  typeid INT4 CONSTRAINT netbox_type_fkey REFERENCES type ON UPDATE CASCADE ON DELETE CASCADE,
  deviceid INT4 NOT NULL CONSTRAINT netbox_device_fkey REFERENCES device ON UPDATE CASCADE ON DELETE CASCADE,
  sysname VARCHAR UNIQUE,
  catid VARCHAR(8) NOT NULL CONSTRAINT netbox_cat_fkey REFERENCES cat ON UPDATE CASCADE ON DELETE CASCADE,
  subcat VARCHAR,
  orgid VARCHAR(30) NOT NULL CONSTRAINT netbox_org_fkey REFERENCES org ON UPDATE CASCADE,
  ro VARCHAR,
  rw VARCHAR,
  prefixid INT4 CONSTRAINT netbox_prefix_fkey REFERENCES prefix ON UPDATE CASCADE ON DELETE SET null,
  up CHAR(1) NOT NULL DEFAULT 'y' CHECK (up='y' OR up='n' OR up='s'), -- y=up, n=down, s=shadow
  snmp_version INT4 NOT NULL DEFAULT 1,
  snmp_agent VARCHAR,
  upsince TIMESTAMP NOT NULL DEFAULT NOW(),
  uptodate BOOLEAN NOT NULL DEFAULT false, 
  discovered TIMESTAMP NULL DEFAULT NOW(),
  UNIQUE(ip),
  UNIQUE(deviceid)
);
CREATE INDEX netbox_prefixid_btree ON netbox USING btree (prefixid);

CREATE TABLE netboxsnmpoid (
  netboxid INT4 REFERENCES netbox ON UPDATE CASCADE ON DELETE CASCADE,
  snmpoidid INT4 REFERENCES snmpoid ON UPDATE CASCADE ON DELETE CASCADE,
  frequency INT4,
  UNIQUE(netboxid, snmpoidid)
);  
CREATE INDEX netboxsnmpoid_snmpoidid_btree ON netboxsnmpoid USING btree (snmpoidid);

CREATE TABLE netbox_vtpvlan (
  id SERIAL,
  netboxid INT4 REFERENCES netbox ON UPDATE CASCADE ON DELETE CASCADE,
  vtpvlan INT4,
  PRIMARY KEY(id),
  UNIQUE(netboxid, vtpvlan)
);

CREATE TABLE subcat (
    subcatid VARCHAR,
    descr VARCHAR NOT NULL,
    catid VARCHAR(8) NOT NULL REFERENCES cat(catid),
    PRIMARY KEY (subcatid)
);
INSERT INTO subcat (subcatid,descr,catid) VALUES ('AD','Description','SRV');
INSERT INTO subcat (subcatid,descr,catid) VALUES ('ADC','Description','SRV');
INSERT INTO subcat (subcatid,descr,catid) VALUES ('BACKUP','Description','SRV');
INSERT INTO subcat (subcatid,descr,catid) VALUES ('DNS','Description','SRV');
INSERT INTO subcat (subcatid,descr,catid) VALUES ('FS','Description','SRV');
INSERT INTO subcat (subcatid,descr,catid) VALUES ('LDAP','Description','SRV');
INSERT INTO subcat (subcatid,descr,catid) VALUES ('MAIL','Description','SRV');
INSERT INTO subcat (subcatid,descr,catid) VALUES ('NOTES','Description','SRV');
INSERT INTO subcat (subcatid,descr,catid) VALUES ('STORE','Description','SRV');
INSERT INTO subcat (subcatid,descr,catid) VALUES ('TEST','Description','SRV');
INSERT INTO subcat (subcatid,descr,catid) VALUES ('UNIX','Description','SRV');
INSERT INTO subcat (subcatid,descr,catid) VALUES ('UNIX-STUD','Description','SRV');
INSERT INTO subcat (subcatid,descr,catid) VALUES ('WEB','Description','SRV');
INSERT INTO subcat (subcatid,descr,catid) VALUES ('WIN','Description','SRV');
INSERT INTO subcat (subcatid,descr,catid) VALUES ('WIN-STUD','Description','SRV'
);

CREATE TABLE netboxcategory (
  id SERIAL,
  netboxid INT4 NOT NULL REFERENCES netbox ON UPDATE CASCADE ON DELETE CASCADE,
  category VARCHAR NOT NULL REFERENCES subcat ON UPDATE CASCADE ON DELETE CASCADE,
  PRIMARY KEY(netboxid, category)
);


CREATE TABLE netboxinfo (
  netboxinfoid SERIAL PRIMARY KEY,
  netboxid INT4 NOT NULL REFERENCES netbox ON UPDATE CASCADE ON DELETE CASCADE,
  key VARCHAR,
  var VARCHAR NOT NULL,
  val TEXT NOT NULL,
  UNIQUE(netboxid, key, var, val)
);

CREATE TABLE module (
  moduleid SERIAL PRIMARY KEY,
  deviceid INT4 NOT NULL REFERENCES device ON UPDATE CASCADE ON DELETE CASCADE,
  netboxid INT4 NOT NULL REFERENCES netbox ON UPDATE CASCADE ON DELETE CASCADE,
  module INT4 NOT NULL,
  model VARCHAR,
  descr VARCHAR,
  up CHAR(1) NOT NULL DEFAULT 'y' CHECK (up='y' OR up='n'), -- y=up, n=down
  downsince TIMESTAMP,
  UNIQUE (netboxid, module),
  UNIQUE(deviceid)
);

CREATE TABLE mem (
  memid SERIAL PRIMARY KEY,
  netboxid INT4 NOT NULL REFERENCES netbox ON UPDATE CASCADE ON DELETE CASCADE,
  memtype VARCHAR NOT NULL,
  device VARCHAR NOT NULL,
  size INT4 NOT NULL,
  used INT4,
  UNIQUE(netboxid, memtype, device)
);


CREATE TABLE swport (
  swportid SERIAL PRIMARY KEY,
  moduleid INT4 NOT NULL REFERENCES module ON UPDATE CASCADE ON DELETE CASCADE,
  ifindex INT4 NOT NULL,
  port INT4,
  interface VARCHAR,
  link CHAR(1) CHECK (link='y' OR link='n' OR link='d'), -- y=up, n=down (operDown), d=down (admDown)
  speed DOUBLE PRECISION,
  duplex CHAR(1) CHECK (duplex='f' OR duplex='h'), -- f=full, h=half
  media VARCHAR,
  vlan INT,
  trunk BOOL,
  portname VARCHAR,
  to_netboxid INT4 REFERENCES netbox (netboxid) ON UPDATE CASCADE ON DELETE SET NULL,
  to_swportid INT4 REFERENCES swport (swportid) ON UPDATE CASCADE ON DELETE SET NULL,
  UNIQUE(moduleid, ifindex)
);

CREATE TABLE swp_netbox (
  swp_netboxid SERIAL PRIMARY KEY,
  netboxid INT4 NOT NULL REFERENCES netbox ON UPDATE CASCADE ON DELETE CASCADE,
  ifindex INT4 NOT NULL,
  to_netboxid INT4 NOT NULL REFERENCES netbox ON UPDATE CASCADE ON DELETE CASCADE,
  to_swportid INT4 REFERENCES swport (swportid) ON UPDATE CASCADE ON DELETE SET NULL,
  misscnt INT4 NOT NULL DEFAULT '0',
  UNIQUE(netboxid, ifindex, to_netboxid)
);

CREATE TABLE gwport (
  gwportid SERIAL PRIMARY KEY,
  moduleid INT4 NOT NULL REFERENCES module ON UPDATE CASCADE ON DELETE CASCADE,
  ifindex INT4 NOT NULL,
  link CHAR(1) CHECK (link='y' OR link='n' OR link='d'), -- y=up, n=down (operDown), d=down (admDown)
  masterindex INT4,
  interface VARCHAR,
  speed DOUBLE PRECISION NOT NULL,
  metric INT4,
  portname VARCHAR,
  to_netboxid INT4 REFERENCES netbox (netboxid) ON UPDATE CASCADE ON DELETE SET NULL,
  to_swportid INT4 REFERENCES swport (swportid) ON UPDATE CASCADE ON DELETE SET NULL,
  UNIQUE(moduleid, ifindex)
);
CREATE INDEX gwport_to_swportid_btree ON gwport USING btree (to_swportid);

CREATE TABLE gwportprefix (
  gwportid INT4 NOT NULL REFERENCES gwport ON UPDATE CASCADE ON DELETE CASCADE,
  prefixid INT4 NOT NULL REFERENCES prefix ON UPDATE CASCADE ON DELETE CASCADE,
  gwip INET NOT NULL,
  hsrp BOOL NOT NULL DEFAULT false,
  UNIQUE(gwip)
);
CREATE INDEX gwportprefix_gwportid_btree ON gwportprefix USING btree (gwportid);
CREATE INDEX gwportprefix_prefixid_btree ON gwportprefix USING btree (prefixid);

CREATE TABLE swportvlan (
  swportvlanid SERIAL PRIMARY KEY,
  swportid INT4 NOT NULL REFERENCES swport ON UPDATE CASCADE ON DELETE CASCADE,
  vlanid INT4 NOT NULL REFERENCES vlan ON UPDATE CASCADE ON DELETE CASCADE,
  direction CHAR(1) NOT NULL DEFAULT 'x', -- u=up, d=down, ...
  UNIQUE (swportid, vlanid)
);
CREATE INDEX swportvlan_swportid_btree ON swportvlan USING btree (swportid);
CREATE INDEX swportvlan_vlanid_btree ON swportvlan USING btree (vlanid);

CREATE TABLE swportallowedvlan (
  swportid INT4 NOT NULL PRIMARY KEY REFERENCES swport ON UPDATE CASCADE ON DELETE CASCADE,
  hexstring VARCHAR
);


CREATE TABLE swportblocked (
  swportid INT4 NOT NULL REFERENCES swport ON UPDATE CASCADE ON DELETE CASCADE,
  vlan INT4 NOT NULL,
  PRIMARY KEY(swportid, vlan)
);

CREATE TABLE alertengine (
	lastalertqid integer
);

INSERT INTO alertengine (lastalertqid) values(0);

CREATE TABLE cabling (
  cablingid SERIAL PRIMARY KEY,
  roomid VARCHAR(30) NOT NULL REFERENCES room ON UPDATE CASCADE ON DELETE CASCADE,
  jack VARCHAR NOT NULL,
  building VARCHAR NOT NULL,
  targetroom VARCHAR NOT NULL,
  descr VARCHAR,
  category VARCHAR NOT NULL,
UNIQUE(roomid,jack));

CREATE TABLE patch (
  patchid SERIAL PRIMARY KEY,
  swportid INT4 NOT NULL REFERENCES swport ON UPDATE CASCADE ON DELETE CASCADE,
  cablingid INT4 NOT NULL REFERENCES cabling ON UPDATE CASCADE ON DELETE CASCADE,
  split VARCHAR NOT NULL DEFAULT 'no',
UNIQUE(swportid,cablingid));


------------------------------------------------------------------
------------------------------------------------------------------


-- Attach a trigger to arp and cam, to make sure records are closed as
-- netboxes are deleted.
-- The pl/pgsql scripting language must be installed on this database first.
CREATE FUNCTION netboxid_null_upd_end_time () RETURNS trigger AS
  'BEGIN
     IF old.netboxid IS NOT NULL AND new.netboxid IS NULL THEN
       new.end_time = current_timestamp;
     END IF;
     RETURN new;
   end' LANGUAGE plpgsql;

CREATE TABLE arp (
  arpid SERIAL PRIMARY KEY,
  netboxid INT4 REFERENCES netbox ON UPDATE CASCADE ON DELETE SET NULL,
  prefixid INT4 REFERENCES prefix ON UPDATE CASCADE ON DELETE SET NULL,
  sysname VARCHAR NOT NULL,
  ip INET NOT NULL,
  mac MACADDR NOT NULL,
  start_time TIMESTAMP NOT NULL,
  end_time TIMESTAMP NOT NULL DEFAULT 'infinity'
);
CREATE TRIGGER update_arp BEFORE UPDATE ON arp FOR EACH ROW EXECUTE PROCEDURE netboxid_null_upd_end_time();
CREATE INDEX arp_mac_btree ON arp USING btree (mac);
CREATE INDEX arp_ip_btree ON arp USING btree (ip);
CREATE INDEX arp_start_time_btree ON arp USING btree (start_time);
CREATE INDEX arp_end_time_btree ON arp USING btree (end_time);
CREATE INDEX arp_prefixid_btree ON arp USING btree (prefixid);

-- Rule to automatically close arp entries related to a given prefix
CREATE RULE close_arp_prefices AS ON DELETE TO prefix
  DO UPDATE arp SET end_time=NOW(), prefixid=NULL 
     WHERE prefixid=OLD.prefixid;

CREATE TABLE cam (
  camid SERIAL PRIMARY KEY,
  netboxid INT4 REFERENCES netbox ON UPDATE CASCADE ON DELETE SET NULL,
  sysname VARCHAR NOT NULL,
  ifindex INT4 NOT NULL,
  module VARCHAR(4),
  port VARCHAR,
  mac MACADDR NOT NULL,
  start_time TIMESTAMP NOT NULL,
  end_time TIMESTAMP NOT NULL DEFAULT 'infinity',
  misscnt INT4 DEFAULT '0',
  UNIQUE(netboxid,sysname,module,port,mac,start_time)
);
CREATE TRIGGER update_cam BEFORE UPDATE ON cam FOR EACH ROW EXECUTE PROCEDURE netboxid_null_upd_end_time();
CREATE INDEX cam_mac_btree ON cam USING btree (mac);
CREATE INDEX cam_start_time_btree ON cam USING btree (start_time);
CREATE INDEX cam_end_time_btree ON cam USING btree (end_time);
CREATE INDEX cam_misscnt_btree ON cam USING btree (misscnt);


-- VIEWs -----------------------
CREATE VIEW netboxmac AS  
(SELECT DISTINCT ON (mac) netbox.netboxid, arp.mac
 FROM netbox
 JOIN arp ON (arp.arpid = (SELECT arp.arpid FROM arp WHERE arp.ip=netbox.ip AND end_time='infinity' LIMIT 1)))
UNION DISTINCT
(SELECT DISTINCT ON (mac) module.netboxid,mac
 FROM arp
 JOIN gwportprefix gwp ON
  (arp.ip=gwp.gwip AND (hsrp=true OR (SELECT COUNT(*) FROM gwportprefix WHERE gwp.prefixid=gwportprefix.prefixid AND hsrp=true) = 0))
 JOIN gwport USING(gwportid)
 JOIN module USING (moduleid)
 WHERE arp.end_time='infinity');

CREATE VIEW prefix_active_ip_cnt AS
(SELECT prefix.prefixid, COUNT(arp.ip) AS active_ip_cnt
 FROM prefix
 LEFT JOIN arp ON arp.ip << prefix.netaddr
 WHERE arp.end_time = 'infinity'
 GROUP BY prefix.prefixid);

CREATE VIEW prefix_max_ip_cnt AS
(SELECT prefixid,
  CASE POW(2,32-MASKLEN(netaddr))-2 WHEN -1 THEN 0
   ELSE
  POW(2,32-MASKLEN(netaddr))-2 END AS max_ip_cnt
 FROM prefix);

-- This view gives the allowed vlan for a given hexstring i swportallowedvlan
CREATE TABLE range (
  num INT NOT NULL PRIMARY KEY
);
INSERT INTO range VALUES (0);
INSERT INTO range (SELECT num+(SELECT COUNT(*) FROM range) FROM range);
INSERT INTO range (SELECT num+(SELECT COUNT(*) FROM range) FROM range);
INSERT INTO range (SELECT num+(SELECT COUNT(*) FROM range) FROM range);
INSERT INTO range (SELECT num+(SELECT COUNT(*) FROM range) FROM range);
INSERT INTO range (SELECT num+(SELECT COUNT(*) FROM range) FROM range);
INSERT INTO range (SELECT num+(SELECT COUNT(*) FROM range) FROM range);
INSERT INTO range (SELECT num+(SELECT COUNT(*) FROM range) FROM range);
INSERT INTO range (SELECT num+(SELECT COUNT(*) FROM range) FROM range);
INSERT INTO range (SELECT num+(SELECT COUNT(*) FROM range) FROM range);
INSERT INTO range (SELECT num+(SELECT COUNT(*) FROM range) FROM range);
DELETE FROM range WHERE num >= 1000;

CREATE VIEW allowedvlan AS
  (SELECT swportid,num AS allowedvlan FROM swportallowedvlan CROSS JOIN range
    WHERE num < length(decode(hexstring,'hex'))*8 AND (CASE WHEN length(hexstring)=256
    THEN get_bit(decode(hexstring,'hex'),(num/8)*8+7-(num%8))
    ELSE get_bit(decode(hexstring,'hex'),(length(decode(hexstring,'hex'))*8-num+7>>3<<3)-8+(num%8))
    END)=1);

CREATE VIEW allowedvlan_both AS
  (select swportid,swportid as swportid2,allowedvlan from allowedvlan ORDER BY allowedvlan) union
  (select  swport.swportid,to_swportid as swportid2,allowedvlan from swport join allowedvlan
    on (swport.to_swportid=allowedvlan.swportid) ORDER BY allowedvlan);

-------- vlanPlot tables ------
CREATE TABLE vp_netbox_grp_info (
  vp_netbox_grp_infoid SERIAL PRIMARY KEY,
  name VARCHAR NOT NULL,
  hideicons BOOL NOT NULL DEFAULT false,
  iconname VARCHAR,
  x INT4 NOT NULL DEFAULT '0',
  y INT4 NOT NULL DEFAULT '0'
);
-- Default network
INSERT INTO vp_netbox_grp_info (vp_netbox_grp_infoid,name,hideicons) VALUES (0,'_Top',false);

CREATE TABLE vp_netbox_grp (
  vp_netbox_grp_infoid INT4 REFERENCES vp_netbox_grp_info ON UPDATE CASCADE ON DELETE CASCADE,
  pnetboxid INT4 NOT NULL,
  UNIQUE(vp_netbox_grp_infoid, pnetboxid)
);

CREATE TABLE vp_netbox_xy (
  vp_netbox_xyid SERIAL PRIMARY KEY, 
  pnetboxid INT4 NOT NULL,
  x INT4 NOT NULL,
  y INT4 NOT NULL,
  vp_netbox_grp_infoid INT4 NOT NULL REFERENCES vp_netbox_grp_info ON UPDATE CASCADE ON DELETE CASCADE,
  UNIQUE(pnetboxid, vp_netbox_grp_infoid)
);


-------- vlanPlot end ------

------------------------------------------------------------------------------
-- rrd metadb tables
------------------------------------------------------------------------------

-- This table contains the different systems that has rrd-data.
-- Replaces table eventprocess
CREATE TABLE subsystem (
  name      VARCHAR PRIMARY KEY, -- name of the system, e.g. Cricket
  descr     VARCHAR  -- description of the system
);

INSERT INTO subsystem (name) VALUES ('eventEngine');
INSERT INTO subsystem (name) VALUES ('pping');
INSERT INTO subsystem (name) VALUES ('serviceping');
INSERT INTO subsystem (name) VALUES ('moduleMon');
INSERT INTO subsystem (name) VALUES ('thresholdMon');
INSERT INTO subsystem (name) VALUES ('trapParser');
INSERT INTO subsystem (name) VALUES ('cricket');
INSERT INTO subsystem (name) VALUES ('deviceManagement');
INSERT INTO subsystem (name) VALUES ('getDeviceData');
INSERT INTO subsystem (name) VALUES ('devBrowse');
INSERT INTO subsystem (name) VALUES ('maintenance');
INSERT INTO subsystem (name) VALUES ('snmptrapd');

-- Each rrdfile should be registered here. We need the path to find it,
-- and also a link to which unit or service it has data about to easily be
-- able to select all relevant files to a unit or service. Key and value
-- are meant to be combined and thereby point to a specific row in the db.
CREATE TABLE rrd_file (
  rrd_fileid    SERIAL PRIMARY KEY,
  path      VARCHAR NOT NULL, -- complete path to the rrdfile
  filename  VARCHAR NOT NULL, -- name of the rrdfile (including the .rrd)
  step      INT, -- the number of seconds between each update
  subsystem VARCHAR REFERENCES subsystem (name) ON UPDATE CASCADE ON DELETE CASCADE,
  netboxid  INT REFERENCES netbox ON UPDATE CASCADE ON DELETE SET NULL,
  key       VARCHAR,
  value     VARCHAR
);

-- Each datasource for each rrdfile is registered here. We need the name and
-- desc for instance in Cricket. Cricket has the name ds0, ds1 and so on, and
-- to understand what that is for humans we need the descr.
CREATE TABLE rrd_datasource (
  rrd_datasourceid  SERIAL PRIMARY KEY,
  rrd_fileid        INT REFERENCES rrd_file ON UPDATE CASCADE ON DELETE CASCADE,
  name          VARCHAR, -- name of the datasource in the file
  descr         VARCHAR, -- human-understandable name of the datasource
  dstype        VARCHAR CHECK (dstype='GAUGE' OR dstype='DERIVE' OR dstype='COUNTER' OR dstype='ABSOLUTE'),
  units         VARCHAR, -- textual decription of the y-axis (percent, kilo, giga, etc.)
  threshold VARCHAR,
  max   VARCHAR,
  delimiter CHAR(1) CHECK (delimiter='>' OR delimiter='<'),
  thresholdstate VARCHAR CHECK (thresholdstate='active' OR thresholdstate='inactive')
);


-- 
CREATE VIEW rrddatasourcenetbox AS
(SELECT DISTINCT rrd_datasource.descr, rrd_datasource.rrd_datasourceid, sysname
  FROM rrd_datasource
  JOIN rrd_file USING (rrd_fileid)
  JOIN netbox USING (netboxid));

------------------------------------------------------------------------------------------
-- event system tables
------------------------------------------------------------------------------------------

-- event tables
CREATE TABLE eventtype (
  eventtypeid VARCHAR(32) PRIMARY KEY,
  eventtypedesc VARCHAR,
  stateful CHAR(1) NOT NULL CHECK (stateful='y' OR stateful='n')
);
INSERT INTO eventtype (eventtypeid,eventtypedesc,stateful) VALUES 
  ('boxState','Tells us whether a network-unit is down or up.','y');
INSERT INTO eventtype (eventtypeid,eventtypedesc,stateful) VALUES 
  ('serviceState','Tells us whether a service on a server is up or down.','y');
INSERT INTO eventtype (eventtypeid,eventtypedesc,stateful) VALUES
  ('moduleState','Tells us whether a module in a device is working or not.','y');
INSERT INTO eventtype (eventtypeid,eventtypedesc,stateful) VALUES
  ('thresholdState','Tells us whether the load has passed a certain threshold.','y');
INSERT INTO eventtype (eventtypeid,eventtypedesc,stateful) VALUES
  ('linkState','Tells us whether a link is up or down.','y');
INSERT INTO eventtype (eventtypeid,eventtypedesc,stateful) VALUES
  ('boxRestart','Tells us that a network-unit has done a restart','n');
INSERT INTO eventtype (eventtypeid,eventtypedesc,stateful) VALUES
  ('info','Basic information','n');
INSERT INTO eventtype (eventtypeid,eventtypedesc,stateful) VALUES
  ('notification','Notification event, typically between NAV systems','n');
INSERT INTO eventtype (eventtypeid,eventtypedesc,stateful) VALUES
    ('deviceActive','Lifetime event for a device','y');
INSERT INTO eventtype (eventtypeid,eventtypedesc,stateful) VALUES
    ('deviceState','Registers the state of a device','y');
INSERT INTO eventtype (eventtypeid,eventtypedesc,stateful) VALUES
    ('deviceNotice','Registers a notice on a device','n');
INSERT INTO eventtype (eventtypeid,eventtypedesc,stateful) VALUES
    ('maintenanceState','Tells us if something is set on maintenance','y');

CREATE TABLE eventq (
  eventqid SERIAL PRIMARY KEY,
  source VARCHAR(32) NOT NULL REFERENCES subsystem (name) ON UPDATE CASCADE ON DELETE CASCADE,
  target VARCHAR(32) NOT NULL REFERENCES subsystem (name) ON UPDATE CASCADE ON DELETE CASCADE,
  deviceid INT4 REFERENCES device ON UPDATE CASCADE ON DELETE CASCADE,
  netboxid INT4 REFERENCES netbox ON UPDATE CASCADE ON DELETE CASCADE,
  subid VARCHAR,
  time TIMESTAMP NOT NULL DEFAULT NOW (),
  eventtypeid VARCHAR(32) NOT NULL REFERENCES eventtype ON UPDATE CASCADE ON DELETE CASCADE,
  state CHAR(1) NOT NULL DEFAULT 'x' CHECK (state='x' OR state='s' OR state='e'), -- x = stateless, s = start, e = end
  value INT4 NOT NULL DEFAULT '100',
  severity INT4 NOT NULL DEFAULT '50'
);
CREATE INDEX eventq_target_btree ON eventq USING btree (target);
CREATE TABLE eventqvar (
  eventqid INT4 REFERENCES eventq ON UPDATE CASCADE ON DELETE CASCADE,
  var VARCHAR NOT NULL,
  val TEXT NOT NULL,
  UNIQUE(eventqid, var) -- only one val per var per event
);
CREATE INDEX eventqvar_eventqid_btree ON eventqvar USING btree (eventqid);



-- alert tables

CREATE TABLE alerttype (
  alerttypeid SERIAL PRIMARY KEY,
  eventtypeid VARCHAR(32) NOT NULL REFERENCES eventtype ON UPDATE CASCADE ON DELETE CASCADE,
  alerttype VARCHAR,
  alerttypedesc VARCHAR,
  CONSTRAINT alerttype_eventalert_unique UNIQUE (eventtypeid, alerttype)
);
INSERT INTO alerttype (eventtypeid,alerttype,alerttypedesc) VALUES
  ('boxState','boxDownWarning','Warning sent before declaring the box down.');
INSERT INTO alerttype (eventtypeid,alerttype,alerttypedesc) VALUES
  ('boxState','boxShadowWarning','Warning sent before declaring the box in shadow.');
INSERT INTO alerttype (eventtypeid,alerttype,alerttypedesc) VALUES
  ('boxState','boxDown','Box declared down.');
INSERT INTO alerttype (eventtypeid,alerttype,alerttypedesc) VALUES
  ('boxState','boxUp','Box declared up.');
INSERT INTO alerttype (eventtypeid,alerttype,alerttypedesc) VALUES
  ('boxState','boxShadow','Box declared down, but is in shadow.');
INSERT INTO alerttype (eventtypeid,alerttype,alerttypedesc) VALUES
  ('boxState','boxSunny','Box declared up from a previous shadow state.');
INSERT INTO alerttype (eventtypeid,alerttype,alerttypedesc) VALUES
  ('moduleState','moduleDownWarning','Warning sent before declaring the module down.');
INSERT INTO alerttype (eventtypeid,alerttype,alerttypedesc) VALUES
  ('moduleState','moduleDown','Module declared down.');
INSERT INTO alerttype (eventtypeid,alerttype,alerttypedesc) VALUES
  ('moduleState','moduleUp','Module declared up.');
INSERT INTO alerttype (eventtypeid,alerttype,alerttypedesc) VALUES
  ('serviceState','httpDown','http service not responding.');
INSERT INTO alerttype (eventtypeid,alerttype,alerttypedesc) VALUES
  ('serviceState','httpUp','http service responding.');
INSERT INTO alerttype (eventtypeid,alerttype,alerttypedesc) VALUES
  ('maintenanceState','onMaintenance','Box put on maintenance.');
INSERT INTO alerttype (eventtypeid,alerttype,alerttypedesc) VALUES
  ('maintenanceState','offMaintenance','Box taken off maintenance.');
INSERT INTO alerttype (eventtypeid,alerttype,alerttypedesc) VALUES
  ('thresholdState','exceededThreshold','Threshold exceeded.');
INSERT INTO alerttype (eventtypeid,alerttype,alerttypedesc) VALUES
  ('thresholdState','belowThreshold','Value below threshold.');
INSERT INTO alerttype (eventtypeid,alerttype,alerttypedesc) VALUES
  ('info','dnsMismatch','Mismatch between sysname and dnsname.');
INSERT INTO alerttype (eventtypeid,alerttype,alerttypedesc) VALUES
  ('info','serialChanged','Serial number for the device has changed.');
INSERT INTO alerttype (eventtypeid,alerttype,alerttypedesc) VALUES
  ('boxRestart','coldStart','Tells us that a network-unit has done a coldstart.');
INSERT INTO alerttype (eventtypeid,alerttype,alerttypedesc) VALUES
  ('boxRestart','warmStart','Tells us that a network-unit has done a warmstart.');
INSERT INTO alerttype (eventtypeid,alerttype,alerttypedesc) VALUES
  ('deviceState','deviceInIPOperation','Device is in operation as a box.');
INSERT INTO alerttype (eventtypeid,alerttype,alerttypedesc) VALUES
  ('deviceState','deviceInStack','Device is in operation as a module.');
INSERT INTO alerttype (eventtypeid,alerttype,alerttypedesc) VALUES
  ('deviceState','deviceRMA','RMA event for device.');
INSERT INTO alerttype (eventtypeid,alerttype,alerttypedesc) VALUES
  ('deviceNotice','deviceError','Error situation on device.');
INSERT INTO alerttype (eventtypeid,alerttype,alerttypedesc) VALUES
  ('deviceNotice','deviceSwUpgrade','Software upgrade on device.');
INSERT INTO alerttype (eventtypeid,alerttype,alerttypedesc) VALUES
  ('deviceNotice','deviceHwUpgrade','Hardware upgrade on device.');


CREATE TABLE alertq (
  alertqid SERIAL PRIMARY KEY,
  source VARCHAR(32) NOT NULL REFERENCES subsystem (name) ON UPDATE CASCADE ON DELETE CASCADE,
  deviceid INT4 REFERENCES device ON UPDATE CASCADE ON DELETE CASCADE,
  netboxid INT4 REFERENCES netbox ON UPDATE CASCADE ON DELETE CASCADE,
  subid VARCHAR,
  time TIMESTAMP NOT NULL,
  eventtypeid VARCHAR(32) REFERENCES eventtype ON UPDATE CASCADE ON DELETE CASCADE,
  alerttypeid INT4 REFERENCES alerttype ON UPDATE CASCADE ON DELETE CASCADE,
  state CHAR(1) NOT NULL,
  value INT4 NOT NULL,
  severity INT4 NOT NULL
);

CREATE TABLE alertqmsg (
  alertqid INT4 REFERENCES alertq ON UPDATE CASCADE ON DELETE CASCADE,
  msgtype VARCHAR NOT NULL,
  language VARCHAR NOT NULL,
  msg TEXT NOT NULL,
  UNIQUE(alertqid, msgtype, language)
);
CREATE INDEX alertqmsg_alertqid_btree ON alertqmsg USING btree (alertqid);
CREATE TABLE alertqvar (
  alertqid INT4 REFERENCES alertq ON UPDATE CASCADE ON DELETE CASCADE,
  var VARCHAR NOT NULL,
  val TEXT NOT NULL,
  UNIQUE(alertqid, var) -- only one val per var per event
);
CREATE INDEX alertqvar_alertqid_btree ON alertqvar USING btree (alertqid);


CREATE TABLE alerthist (
  alerthistid SERIAL PRIMARY KEY,
  source VARCHAR(32) NOT NULL REFERENCES subsystem (name) ON UPDATE CASCADE ON DELETE CASCADE,
  deviceid INT4 REFERENCES device ON UPDATE CASCADE ON DELETE CASCADE,
  netboxid INT4 REFERENCES netbox ON UPDATE CASCADE ON DELETE SET NULL,
  subid VARCHAR,
  start_time TIMESTAMP NOT NULL,
  end_time TIMESTAMP DEFAULT 'infinity',
  eventtypeid VARCHAR(32) NOT NULL REFERENCES eventtype ON UPDATE CASCADE ON DELETE CASCADE,
  alerttypeid INT4 REFERENCES alerttype ON UPDATE CASCADE ON DELETE CASCADE,
  value INT4 NOT NULL,
  severity INT4 NOT NULL
);
CREATE INDEX alerthist_start_time_btree ON alerthist USING btree (start_time);
CREATE INDEX alerthist_end_time_btree ON alerthist USING btree (end_time);

-- Rule to automatically close module related alert states when modules are
-- deleted.
CREATE OR REPLACE RULE close_alerthist_modules AS ON DELETE TO module
  DO UPDATE alerthist SET end_time=NOW() 
     WHERE eventtypeid IN ('moduleState', 'linkState')
       AND end_time='infinity'
       AND deviceid=OLD.deviceid;

CREATE TABLE alerthistmsg (
  alerthistid INT4 REFERENCES alerthist ON UPDATE CASCADE ON DELETE CASCADE,
  state CHAR(1) NOT NULL,
  msgtype VARCHAR NOT NULL,
  language VARCHAR NOT NULL,
  msg TEXT NOT NULL,
  UNIQUE(alerthistid, state, msgtype, language)
);
CREATE INDEX alerthistmsg_alerthistid_btree ON alerthistmsg USING btree (alerthistid);

CREATE TABLE alerthistvar (
  alerthistid INT4 REFERENCES alerthist ON UPDATE CASCADE ON DELETE CASCADE,
  state CHAR(1) NOT NULL,
  var VARCHAR NOT NULL,
  val TEXT NOT NULL,
  UNIQUE(alerthistid, state, var) -- only one val per var per state per alert
);
CREATE INDEX alerthistvar_alerthistid_btree ON alerthistvar USING btree (alerthistid);

------------------------------------------------------------------------------
-- servicemon tables
------------------------------------------------------------------------------

CREATE TABLE service (
  serviceid SERIAL PRIMARY KEY,
  netboxid INT4 REFERENCES netbox ON UPDATE CASCADE ON DELETE CASCADE,
  active BOOL DEFAULT true,
  handler VARCHAR,
  version VARCHAR,
  up CHAR(1) NOT NULL DEFAULT 'y' CHECK (up='y' OR up='n' OR up='s') -- y=up, n=down, s=shadow
);
CREATE RULE rrdfile_deleter AS 
    ON DELETE TO service 
    DO DELETE FROM rrd_file 
        WHERE key='serviceid' AND value=old.serviceid;

CREATE TABLE serviceproperty (
serviceid INT4 NOT NULL REFERENCES service ON UPDATE CASCADE ON DELETE CASCADE,
  property VARCHAR(64) NOT NULL,
  value VARCHAR,
  PRIMARY KEY(serviceid, property)
);

------------------------------------------------------------------------------
-- messages/maintenance v2 tables
------------------------------------------------------------------------------

CREATE TABLE message (
    messageid SERIAL PRIMARY KEY,
    title VARCHAR NOT NULL,
    description TEXT NOT NULL,
    tech_description TEXT,
    publish_start TIMESTAMP,
    publish_end TIMESTAMP,
    author VARCHAR NOT NULL,
    last_changed TIMESTAMP,
    replaces_message INT REFERENCES message,
    replaced_by INT REFERENCES message
);

CREATE OR REPLACE FUNCTION message_replace() RETURNS TRIGGER AS '
    DECLARE
        -- Old replaced_by value of the message beeing replaced
        old_replaced_by INTEGER;
    BEGIN
        -- Remove references that are no longer correct
        IF TG_OP = ''UPDATE'' THEN
            IF OLD.replaces_message <> NEW.replaces_message OR
                (OLD.replaces_message IS NOT NULL AND NEW.replaces_message IS NULL) THEN
                EXECUTE ''UPDATE message SET replaced_by = NULL WHERE messageid = ''
                || quote_literal(OLD.replaces_message);
            END IF;
        END IF;

        -- It does not replace any message, exit
        IF NEW.replaces_message IS NULL THEN
            RETURN NEW;
        END IF;

        -- Update the replaced_by field of the replaced message with a
        -- reference to the replacer
        SELECT INTO old_replaced_by replaced_by FROM message
            WHERE messageid = NEW.replaces_message;
        IF old_replaced_by <> NEW.messageid OR old_replaced_by IS NULL THEN
            EXECUTE ''UPDATE message SET replaced_by = ''
            || quote_literal(NEW.messageid)
            || '' WHERE messageid = ''
            || quote_literal(NEW.replaces_message);
        END IF;

        RETURN NEW;
        END;
    ' language 'plpgsql';

CREATE TRIGGER trig_message_replace
	AFTER INSERT OR UPDATE ON message
	FOR EACH ROW
	EXECUTE PROCEDURE message_replace();

CREATE OR REPLACE VIEW message_with_replaced AS
    SELECT
        m.messageid, m.title,
	m.description, m.tech_description,
        m.publish_start, m.publish_end, m.author, m.last_changed,
        m.replaces_message, m.replaced_by,
        rm.title AS replaces_message_title,
        rm.description AS replaces_message_description,
        rm.tech_description AS replaces_message_tech_description,
        rm.publish_start AS replaces_message_publish_start,
        rm.publish_end AS replaces_message_publish_end,
        rm.author AS replaces_message_author,
        rm.last_changed AS replaces_message_last_changed,
        rb.title AS replaced_by_title,
        rb.description AS replaced_by_description,
        rb.tech_description AS replaced_by_tech_description,
        rb.publish_start AS replaced_by_publish_start,
        rb.publish_end AS replaced_by_publish_end,
        rb.author AS replaced_by_author,
        rb.last_changed AS replaced_by_last_changed
    FROM
    	message m LEFT JOIN message rm ON (m.replaces_message = rm.messageid)
    	LEFT JOIN message rb ON (m.replaced_by = rb.messageid);

CREATE TABLE maint_task (
    maint_taskid SERIAL PRIMARY KEY,
    maint_start TIMESTAMP NOT NULL,
    maint_end TIMESTAMP NOT NULL,
    description TEXT NOT NULL,
    author VARCHAR NOT NULL,
    state VARCHAR NOT NULL
);

CREATE TABLE maint_component (
    maint_taskid INT NOT NULL REFERENCES maint_task ON UPDATE CASCADE ON DELETE CASCADE,
    key VARCHAR NOT NULL,
    value VARCHAR NOT NULL,
    PRIMARY KEY (maint_taskid, key, value)
);

CREATE TABLE message_to_maint_task (
    messageid INT NOT NULL REFERENCES message ON UPDATE CASCADE ON DELETE CASCADE,
    maint_taskid INT NOT NULL REFERENCES maint_task ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (messageid, maint_taskid)
);

CREATE OR REPLACE VIEW maint AS
    SELECT * FROM maint_task NATURAL JOIN maint_component;

