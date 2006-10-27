# -*- coding: ISO8859-1 -*-
# $Id$
#
# Copyright 2003, 2004 Norwegian University of Science and Technology
#
# This file is part of Network Administration Visualized (NAV)
#
# NAV is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# NAV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with NAV; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#
# Authors: Hans J�rgen Hoel <hansjorg@orakel.ntnu.no>
#          Sigurd Gartmann <sigurd-nav@brogar.org>
#

from socket import inet_aton,error,gethostbyname,gethostbyaddr
from nav.Snmp import Snmp,NameResolverException,TimeOutException
import nav.db

class Box:
    """
    Object that gets ip,hostname,sysobjectid and snmpversion when initialized
    """


    def __init__(self,identifier,ro):
        """
        Initialize the object, and get all the values set.
        The values = ip, hostname, sysobjectid and snmpversion

        - identifier : hostname or ip
        - ro         : read-only snmp community
        """
        # deviceIdList must be list, not tuple
        self.deviceIdList = []
        self.ro = ro
        (self.hostname,self.ip) = self.getNames(identifier)
        self.typeid = self.getType(identifier,ro)
        self.snmpversion = self.getSnmpVersion(identifier,ro)
        self.serial = None


    def getNames(self,identifier):
        """
        Gets the proper IP-address and hostname, when only one of them are defined.

        - identifier : hostname or ip

        returns (hostname, ip-address)
        """

        #id er hostname
        hostname = identifier
        try:
            ip = gethostbyname(hostname)
        except error, e:

            ip = identifier
            try:
                #id er ip-adresse
                ip = inet_aton(identifier)
                hostname = gethostbyaddr(ip)[0]
                
            except error:
                #raise NameResolverException("No IP-address found for %s" %hostname)
                hostname = ip
        return (hostname,ip)


    def getType(self,identifier,ro):
        """
        Get the type from the nav-type-table. Uses snmp-get and the database to retrieve this information.

        - identifier: hostname or ip-address
        - ro: snmp read-only community

        returns typeid
        """
        
        snmp = Snmp(identifier, ro)

        sql = "select snmpoid from snmpoid where oidkey='typeoid'"
        connection = nav.db.getConnection("bokser")
        handle = connection.cursor()
        handle.execute(sql)
        oid = handle.fetchone()[0]
        
        sysobjectid = snmp.get(oid)
        
        self.sysobjectid = sysobjectid.lstrip(".")

        typeidsql = "select typeid from type where sysobjectid = '%s'"%self.sysobjectid
        handle.execute(typeidsql)
        try:
            typeid = handle.fetchone()[0]
        except TypeError:
            typeid = None

        return typeid

    def __getSerials(self,results):
        """
        Does SQL-queries to get the serial number oids from the database. This
        function does no snmp-querying.  Yes it does!
        """
        snmp = Snmp(self.ip,self.ro,self.snmpversion)
        serials = []
        walkserials = []
        for oidtuple in results:
            oid = oidtuple[0]
            getnext = oidtuple[1]
            if not oid.startswith("."):
                oid = "."+oid
            try:
                if getnext==1:
                    result = snmp.walk(oid.strip())
                    if result:
                        for r in result:
                            if r[1]:
                                walkserials.append(r[1])
                else:
                    result = snmp.get(oid.strip()).strip()
                    if result:
                        serials.append(result)

            except:
                pass

        serials.extend(walkserials)
        self.serials = serials
	self.serial = None
	if len(serials):
	    self.serial = serials[0]
        return serials


    def getDeviceId(self):
        """
        Uses all the defined OIDs for serial number. When doing SNMP-request,
        the SNMP-get-results are prioritised higher than the
        SNMP-walk-results, because SNMP-gets are more likely will get one
        ('the one') serial number for a device.

        This function returns all deviceids for all serial numbers for all
        serial number oids that the device responded on.
        """
        def is_ascii(s):
            """Verify that a string is ASCII encodeable"""
            try:
                s.encode("ascii")
            except UnicodeDecodeError, e:
                return False
            else:
                return True
        
        connection = nav.db.getConnection("bokser")
        handle = connection.cursor()

        serials = []
        sql = "select snmpoid,getnext from snmpoid where oidkey ilike '%serial%'"
        handle.execute(sql)
        results = handle.fetchall()
        serials = self.__getSerials(results)

        devlist = []
        if len(serials):
            escapedSerials = [nav.db.escape(ser.strip()) for ser in serials
                              if is_ascii(ser)]
            whereSerials = ",".join(escapedSerials)
            sql = "SELECT deviceid, productid " \
                  "FROM device " \
                  "WHERE serial IN (%s) " \
                  "      AND deviceid NOT in " \
                  "      (SELECT deviceid FROM netbox)" % whereSerials
            handle.execute(sql)
            for record in handle.fetchall():
                devlist.append(record[0])

        #if devlist:
        self.deviceIdList = devlist
        if len(devlist):
            return devlist[0]
     
    def getSnmpVersion(self,identifier,ro):
        """
        Uses different versions of the snmp-protocol to decide if this box uses version 1 or 2(c) of the protocol

        - identifier: hostname or ip-address
        - ro: snmp read-only community

        returns the protocol version number, 1 or 2 (for 2c)
        """

        snmp = Snmp(identifier,ro,"2c")

        try:
            sysname = snmp.get("1.3.6.1.2.1.1.5.0")
            version = "2c"
        except TimeOutException:

            snmp = Snmp(identifier,ro)
            try:
                sysname = snmp.get("1.3.6.1.2.1.1.5.0")
                version = "1"
            except TimeOutException:
                version = "0"
            
        return version

    def getBoxValues(self):
        """
        Returns all the object's values
        """
        
        return self.hostname,self.ip,self.typeid,self.snmpversion
