# -*- coding: utf-8 -*-
#
# Copyright 2007-2008 UNINETT AS
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
# Authors: Stein Magnus Jodal <stein.magnus.jodal@uninett.no>
#

__copyright__ = "Copyright 2007-2008 UNINETT AS"
__license__ = "GPL"
__author__ = "Stein Magnus Jodal (stein.magnus.jodal@uninett.no)"
__id__ = "$Id$"

from django.conf.urls.defaults import *

from nav.web.ipdevinfo.views import *

# The patterns are relative to the base URL of the subsystem
urlpatterns = patterns('',
    url(r'^$', search,
        name='ipdevinfo-search'),

    # IP Device Details
    url(r'^(?P<name>[\w\d\.-]+)/$', ipdev_details,
        name='ipdevinfo-details-by-name'),
    url(r'^ip=(?P<addr>[a-f\d\.:]+)/$', ipdev_details,
        name='ipdevinfo-details-by-addr'),

    # Module details
    url(r'^(?P<netbox_sysname>[\w\d\.-]+)/module(?P<module_number>\d+)/$',
        module_details, name='ipdevinfo-module-details'),

    # Port details
    url(r'^(?P<netbox_sysname>[\w\d\.-]+)/module(?P<module_number>\d+)/swport(?P<port_id>\d+)/$',
        port_details, {'port_type': 'swport'}, name='ipdevinfo-swport-details'),
    url(r'^(?P<netbox_sysname>[\w\d\.-]+)/module(?P<module_number>\d+)/gwport(?P<port_id>\d+)/$',
        port_details, {'port_type': 'gwport'}, name='ipdevinfo-gwport-details'),
)
