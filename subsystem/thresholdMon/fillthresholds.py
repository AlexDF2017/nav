#!/usr/bin/env python
#
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
# Authors: John Magne Bredal <bredal@itea.ntnu.no>
#
"""
This python script sets the initial thresholds on some of 
the rrd-datasources. This is only meant to be done at install
of NAV-v3, but may be done several times if there is a reason
for that. The script will not overwrite any set thresholds.
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

for datasource in manage.Rrd_datasource.getAllIterator(where="threshold IS NULL"):
#for datasource in manage.Rrd_datasource.getAllIterator():
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
        
