# -*- coding: UTF-8 -*-
#
# Copyright 2007 UNINETT AS
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
# Authors: Kristian Klette <klette@samfundet.no>

import sys
import psycopg
import nav.db

from nav.web.netmapserver.common import *
from nav.web.netmapserver.datacollector import *
from nav.web.netmapserver.output import *

from mod_python import apache, util

from nav.web.templates.GraphML import GraphML

def handler(req):
    connection = nav.db.getConnection('netmapserver', 'manage')
    db = connection.cursor()

    page = GraphML()
    page.netboxes = getData(db)
    req.content_type="text/xml"
    req.send_http_header()
    # Convert the data to readable output and send to the browser
    req.write(page.respond());

    return apache.OK
