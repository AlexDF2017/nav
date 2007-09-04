#!/usr/bin/env python
"""
NAV snmptrapd handler plugin to handle LINKUP and LINKDOWN traps from
network equipment.
"""
import logging
import nav.errors
import re
from nav.db import getConnection
from nav.event import Event

logger = logging.getLogger('nav.snmptrapd.linkupdown')

__copyright__ = "Copyright 2007 Norwegian University of Science and " \
                "Technology\n" \
                "Copyright 2007 UNINETT AS"
__license__ = "GPL"
__author__ = "John-Magne Bredal (john.m.bredal@ntnu.no)"


def handleTrap(trap, config=None):
    """
    handleTrap is run by snmptrapd every time it receives a
    trap. Return False to signal trap was discarded, True if trap was
    accepted.
    """
    db = getConnection('default')
    c = db.cursor()

    # Linkstate-traps are generictypes. Check for linkup/down and post
    # events on eventq.
    if trap.genericType in ['LINKUP','LINKDOWN']:
        logger.debug("Module linkupdown got trap %s %s" % (trap.snmpTrapOID,
                                                           trap.genericType))

        # Initialize eventvariables
        source = 'snmptrapd'
        target = 'eventEngine'
        eventtypeid = 'linkState'

        ifindex = ''
        portOID = config.get('linkupdown','portOID')
        for key, val in trap.varbinds.items():
            if key.find(portOID) >= 0:
                ifindex = val

        netboxid = 0
        deviceid = 0

        # Find netbox and deviceid for this ip-address.
        try:
            query = """SELECT netboxid, vendorid
                       FROM netbox
                       LEFT JOIN type USING (typeid)
                       WHERE ip = %s"""
            logger.debug(query)
            c.execute(query, (trap.src,))
            res = c.dictfetchone()

            netboxid = res['netboxid']

            module = '0'

            # If this is a hp-device we need to create the ifindex
            # according to NAV-standard.
            if res['vendorid'] == 'hp':
                community = trap.community

                # Community in traps from HP-equipment comes in the
                # format sw@[number] where number is the stackmember. 

                if community.find('@') >= 0:
                    try:
                        logger.debug("Moduleinfo %s" %community)
                        module = re.search('\@sw(\d+)', community).groups()[0]
                    except Exception, e:
                        # Didn't find a match for module, can't handle trap
                        logger.debug("No match for module, returning")
                        return False
                
                    # Get correct deviceid
                    deviceq = """SELECT deviceid
                                 FROM module
                                 WHERE netboxid=%s
                                   AND module=%s"""
                    c.execute(deviceq, (netboxid, module))
                    r = c.dictfetchone()
                    deviceid = r['deviceid']

                # Ugly hack to find nav's ifindex
                ifindex = "%s%02d" %(str(int(module) + 1), int(ifindex))

                
        except Exception, why:
            logger.error("Error when querying database: %s" %why)


        # Find swportid
        idquery = """SELECT swportid, module.deviceid, module.module,
                            swport.interface
                     FROM netbox
                     LEFT JOIN module USING (netboxid)
                     LEFT JOIN swport USING (moduleid)
                     WHERE ip=%s AND ifindex = %s""" 
        logger.debug(idquery)
        c.execute(idquery, (trap.src, ifindex))
        idres = c.dictfetchone()

        # Subid is swportid in this case
        subid = idres['swportid']
        interface = idres['interface']
        module = idres['module']

        # The deviceid of the module containing the port
        deviceid = idres['deviceid']

        # Todo: Make sure the events are actually forwarded to alertq
        # for alerting.  It seems like the BoxState-handlerplugin of
        # eventEngine accepts this event but does nothing with it.
        # Thus an alert will never trigger of the events.

        # Check for traptype, post event on queue        
        if trap.genericType == 'LINKUP':
            state = 'e'
            ending = 'up'

            e = Event(source=source, target=target, netboxid=netboxid,
                      deviceid=deviceid, subid=subid, eventtypeid=eventtypeid,
                      state=state)
            e['alerttype'] = 'linkUp'
            e['module'] = module
            e['interface'] = interface

            try:
                e.post()
            except nav.errors.GeneralException, why:
                logger.error(why)
                return False
            
        elif trap.genericType == 'LINKDOWN':
            state = 's'
            ending = 'down'

            e = Event(source=source, target=target, netboxid=netboxid,
                      deviceid=deviceid, subid=subid,
                      eventtypeid=eventtypeid, state=state)

            e['alerttype'] = 'linkDown'
            e['module'] = module
            e['interface'] = interface

            try:
                e.post()
            except nav.errors.GeneralException, why:
                logger.error(why)
                return False


        logger.info("Ifindex %s on %s is %s." %(ifindex, trap.src, ending))

        return True
    else:
        return False


def verifyEventtype ():
    """
    Safe way of verifying that the event- and alarmtypes exist in the
    database. Should be run when module is imported.
    """
    db = getConnection('default')
    c = db.cursor()

    sql = """
    INSERT INTO eventtype (
    SELECT 'linkState','Tells us whether a link is up or down.','y' WHERE NOT EXISTS (
    SELECT * FROM eventtype WHERE eventtypeid = 'linkState'));

    INSERT INTO alertType (
    SELECT nextval('alerttype_alerttypeid_seq'), 'linkState', 'linkUp', 'Link active' WHERE NOT EXISTS (
    SELECT * FROM alerttype WHERE alerttype = 'linkUp'));

    INSERT INTO alertType (
    SELECT nextval('alerttype_alerttypeid_seq'), 'linkState', 'linkDown', 'Link inactive' WHERE NOT EXISTS (
    SELECT * FROM alerttype WHERE alerttype = 'linkDown'));
    """

    queries = sql.split(';')
    for q in queries:
        if len(q.rstrip()) > 0:
            c.execute(q)

    db.commit()
        

# Run verifyeventtype at import
verifyEventtype()
