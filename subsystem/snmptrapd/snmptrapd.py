#!/usr/bin/env python
#
# Copyright 2007 Norwegian University of Science and Technology
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
# Authors: John-Magne Bredal <john.m.bredal@ntnu.no>
#
"""
NAV daemon to receive and act upon SNMP traps.
"""
__copyright__ = "Copyright 2007 Norwegian University of Science and Technology"
__license__ = "GPL"
__author__ = "John-Magne Bredal (john.m.bredal@ntnu.no)"

import os
import sys
import string
from optparse import OptionParser
from nav.db import getConnection
import ConfigParser
import logging

# Import PySNMP modules
from pysnmp import asn1, v1, v2c
from pysnmp import role

# Import NAV libraries
from nav import daemon
import nav.buildconf

# Paths
configfile = nav.buildconf.sysconfdir + "/snmptrapd.conf"
traplogfile = nav.buildconf.localstatedir + "/log/snmptraps.log"
logfile = nav.buildconf.localstatedir + "/log/snmptrapd.log"


def main():

    # Verify subsystem
    verifySubsystem()

    # Initialize defaults
    port = 162
    iface = ''
    community = None

    # Initialize and read startupconfig
    global config
    config = ConfigParser.ConfigParser()
    config.read(configfile)    

    # Check if root
    if os.geteuid() != 0:
        print("Must be root to bind to ports, exiting")
        sys.exit(-1)
    

    # Define options
    usage = "usage: %prog [options] [iface] [community]"
    
    parser = OptionParser(usage)
    parser.add_option("-p", "--port", dest="port", help="Port to bind to, default 162")
    parser.add_option("-d", "--daemon", action="store_true", dest="d", help="Run as daemon")

    # Parse possible options
    global opts
    (opts, args) = parser.parse_args()

    # Parse optional arguments
    if len(args) > 0:
        iface = args[0]
    if len(args) > 1:
        community = args[1]

    # Check if already running 
    pidfile = nav.buildconf.localstatedir + "/run/snmptrapd.pid"
    try:
        daemon.justme(pidfile)
    except daemon.DaemonError, why:
        print why
        sys.exit(-1)

    # Create SNMP agent object
    server = role.manager(iface=(iface, port))
    server.open()

    # We have bound to a port and can safely swith user
    runninguser = config.get('snmptrapd','user')
    try:
        daemon.switchuser(runninguser)
    except daemon.DaemonError, why:
        print why
        server.close()
        sys.exit(-1)


    # logger and traplogger logs to two different files. We want a complete log
    # of received traps in one place, and an activity log somewhere else.
    # Note: When not running in daemonmode the loggers both log to stdout.
    global logger, traplogger

    # If we are to demonize, do it here.
    if opts.d:

        loglevel = config.get('snmptrapd', 'loglevel')
        if not loglevel.isdigit():
            loglevel = logging.getLevelName(loglevel)

        try:
            loglevel = int(loglevel)
        except ValueError:
            #default to loglevel INFO
            loglevel = 20

        # Initialize deamonlogger
        if not loginitfile(logfile, traplogfile, loglevel):
            sys.exit(-1)

        traplogger = logging.getLogger('nav.snmptrapd.traplog')
        logger = logging.getLogger('nav.snmptrapd')


        try:
            print "Going into daemon mode..."
            daemon.daemonize(pidfile)
            logger.info("Snmptrapd started")
            listen(server, community)
        except daemon.DaemonError, why:
            print why
            server.close()
            sys.exit(-1)
          

    else:

        # Log to console
        handler = logging.StreamHandler()

        logger = logging.getLogger('')
        logger.setLevel(logging.DEBUG)
        traplogger = logging.getLogger('')
        traplogger.setLevel(logging.DEBUG)

        logger.addHandler(handler)
        traplogger.addHandler(handler)
        
        # Start listening and exit cleanly if interrupted.
        try:
            logger.info ("Listening on port %s" %port)
            listen(server, community)
        except KeyboardInterrupt, why:
            logger.error( "Received keyboardinterrupt, exiting.")
            server.close()


def listen (server, community):
    """Listen for traps on designed port"""

    
    # Listen for SNMP messages from remote SNMP managers
    while 1:
        # Receive a request message
        (question, src) = server.receive()
        if question is None:
            continue
        
        # Decode request of any version
        (req, rest) = v2c.decode(question)

        # Decode BER encoded Object IDs.
        oids = map(lambda x: x[0], map(asn1.OBJECTID().decode, req['encoded_oids']))
        
        # Decode BER encoded values associated with Object IDs.
        vals = map(lambda x: x[0](), map(asn1.decode, req['encoded_vals']))

        agent = None
        type = None
        genericType = None
        
        varbinds = {}
        # Prepare variables for making of SNMPTrap-object
        if req['version'] == 0:
            agent = str(req['agent_addr'])
            type = str(req['tag'])
            uptime = str(req['time_stamp'])
            # Create snmpoid based on RFC2576
            snmpTrapOID, genericType = transform(req)
        else:
            uptime = vals.pop(0)
            oids.pop(0)
            snmpTrapOID = vals.pop(0)
            oids.pop(0)

        # Add varbinds to array
        for (oid, val) in map(None, oids, vals):
            varbinds[oid] = str(val)

        community = req['community']
        version = str(req['version'] + 1)
        src = src[0]


        # Create trap-object, let handler decide what to do with it.
        trap = SNMPTrap(str(src), agent, type, genericType, snmpTrapOID, uptime, community, version, varbinds)
        trapHandler(trap)

    # Exit nicely
    sys.exit(0)

def transform(req):
    """Transforms from SNMP-v1 to SNMP-v2 format. Returns snmpTrapOID and genericType as string."""

    enterprise = str(req['enterprise'])

    # According to RFC2576 "Coexistence between Version 1, Version 2, and Version 3
    # of the Internet-standard Network Management Framework", we build snmpTrapOID
    # from the snmp-v1 trap by combining enterprise + 0 + specific trap parameter
    # IF the generic trap parameter is 6. If not, the traps are defined as
    # 1.3.6.1.6.3.1.1.5 + generic trap parameter + 1
    for t in v1.GENERIC_TRAP_TYPES.keys():
        if req['generic_trap'] == v1.GENERIC_TRAP_TYPES[t]:
            genericType = t
            if req['generic_trap'] == 6:
                snmpTrapOID = enterprise + ".0." + str(req['specific_trap'])
            else:
                snmpTrapOID = ".1.3.6.1.6.3.1.1.5." + str(req['generic_trap'] + 1)
            break
    else:
        snmpTrapOID = enterprise + ".0." + str(req['specific_trap'])

    return snmpTrapOID, genericType

    

def loginitfile(logfile, traplogfile, loglevel):
    """Initalize the logging handler for logfile."""

    try:
        filehandler = logging.FileHandler(logfile, 'a')
        fileformat = '[%(asctime)s] [%(levelname)s] [pid=%(process)d %(name)s] %(message)s'
        fileformatter = logging.Formatter(fileformat)
        filehandler.setFormatter(fileformatter)
        logger = logging.getLogger()
        logger.addHandler(filehandler)
        logger.setLevel(loglevel)
        #logger.setLevel(loglevel)

        filehandler = logging.FileHandler(traplogfile, 'a')
        filehandler.setFormatter(fileformatter)
        traplogger = logging.getLogger("nav.snmptrapd.traplog")
        traplogger.propagate = 0
        traplogger.addHandler(filehandler)

        return True
    except IOError, error:
        print >> sys.stderr, \
         "Failed creating file loghandler. Daemon mode disabled. (%s)" \
         % error
        return False


def trapHandler(trap):
    """Handle a trap"""

    traplogger.info(trap.trapText())

    # Get name of modules that want traps from configfile, import each
    # module and give them the trap + config for handling.
    
    handlermodules = []
    modulelist = config.get('snmptrapd','handlermodules').split(',')
    for name in modulelist:
        name = name.strip()
        parts = name.split('.')
        parent = '.'.join(parts[:-1])
        try:
            mod = __import__(name, globals(), locals(), [parent])
            handlermodules.append(mod)
        except Exception, why:
            logger.exception("Module %s did not compile - %s" %(name, why))

    for mod in handlermodules:
        try:
            accepted = mod.handleTrap(trap, config=config)
            if accepted:
                logger.debug ("Module %s accepted trap" %mod.__name__)
        except Exception, why:
            logger.exception("Error when handling trap with %s: %s" %(mod.__name__, why))


def verifySubsystem ():
    """Verify that subsystem exists, if not insert it into database"""
    db = getConnection('default')
    c = db.cursor()

    sql = "INSERT INTO subsystem (SELECT 'snmptrapd', '' WHERE NOT EXISTS (SELECT * FROM subsystem WHERE name = 'snmptrapd'))"
    c.execute(sql)
    db.commit()
    

class SNMPTrap:
    """Generic trap-class"""

    def __init__(self, src, agent, type, genericType, snmpTrapOID, uptime, community, version, varbinds):
        self.src = src
        self.agent = agent
        self.type = type
        self.genericType = genericType
        self.snmpTrapOID = snmpTrapOID
        self.uptime = uptime
        self.community = community
        self.varbinds = varbinds
        self.version = version
        # Print string if printable else assume hex and write hex-string
        for key,val in self.varbinds.items():
            if not val.strip(string.printable) == '':
                val = ':'.join(["%02x" % ord(c) for c in val])
                self.varbinds[key] = val


    def __str__(self):
        text = self.trapText()
        return text

    def trapText(self):
        """Creates a textual description of the trap suitable for printing to log or stdout."""
        text = "Got snmp version %s trap\n" %self.version
        text = text + "Src: %s, Community: %s, Uptime: %s\n" %(self.src, self.community, self.uptime)
        text = text + "Type %s, snmpTrapOID: %s\n" %(self.genericType, self.snmpTrapOID)

        keys = self.varbinds.keys()
        keys.sort()
        for key in keys:
            val = self.varbinds[key]
            text = text + "%s -> %s\n" %(key, val)

        return text



if __name__ == '__main__':
    main()

