#!/usr/bin/env python
"""
$Id$

This file is part of the NAV project.

This python script sets the initial thresholds on some of 
the rrd-datasources. This is only meant to be done at install
of NAV-v3, but may be done several times if there is a reason
for that. The script will not overwrite any set thresholds.

Copyright (c) 2003 by NTNU, ITEA nettgruppen
Authors: John Magne Bredal <bredal@itea.ntnu.no>
"""

import psycopg
import forgetSQL
import re
import nav.db.forgotten
from nav import db

conn = db.getConnection('thresholdmon','manage')

from nav.db import manage

nav.db.forgotten.manage._Wrapper.cursor = conn.cursor
nav.db.forgotten.manage._Wrapper._dbModule = psycopg

def setData (datasource,threshold,max):
    datasource.threshold = threshold
    datasource.max = max
    datasource.delimiter = ">"
    datasource.thresholdstate = "inactive"
    datasource.save()

# setting default threshold
default = "90"

#for datasource in manage.Rrd_datasource.getAllIterator(where="threshold IS NULL"):
for datasource in manage.Rrd_datasource.getAllIterator():
    if datasource.units == '%' or datasource.units == '-%':
        print "Found percent %s: %s, setting threshold=%s, max=100" %(datasource.descr,datasource.units, default)
        setData(datasource,default,"100")
    elif re.compile("octets",re.I).search(datasource.descr):
        # Finds the speed of the interface
        rrdfile = datasource.rrd_file

	if (rrdfile.key == 'swport'):
            port = manage.Swport(rrdfile.value)
	else:
	    port = manage.Gwport(rrdfile.value)

        try:
            port.load()
        except forgetSQL.NotFound:
            #print "Faen! %s-%s finnes ikke i databasen???" %(rrdfile.key,rrdfile.value)
            continue

        if port.speed:
            speed = int(port.speed * 2 ** 20)
        
        print "Found octets: %s, setting threshold to %s, max=%s" %(datasource.descr, default+"%", speed);
        setData(datasource,default+"%",speed)        
    else:
	pass
        #print "Fant ingen m�te � sette threshold og max p� for %s" %datasource.descr
        
