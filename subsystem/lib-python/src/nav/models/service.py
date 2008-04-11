# -*- coding: utf-8 -*-
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
# Authors: Stein Magnus Jodal <stein.magnus.jodal@uninett.no>
#

"""Django ORM wrapper for the NAV manage database"""

__copyright__ = "Copyright 2007 UNINETT AS"
__license__ = "GPL"
__author__ = "Stein Magnus Jodal (stein.magnus.jodal@uninett.no)"
__id__ = "$Id$"

from django.db import models

from nav.models.manage import Netbox

class Service(models.Model):
    """From MetaNAV: The service table defines the services on a netbox that
    serviceMon monitors."""

    UP_UP = 'y'
    UP_DOWN = 'n'
    UP_SHADOW = 's'
    UP_CHOICES = (
        (UP_UP, 'up'),
        (UP_DOWN, 'down'),
        (UP_SHADOW, 'shadow'),
    )
    TIME_FRAMES = ('day', 'week', 'month')

    id = models.IntegerField(db_column='serviceid', primary_key=True)
    netbox = models.ForeignKey(Netbox, db_column='netboxid')
    active = models.BooleanField(default=True)
    handler = models.CharField(max_length=-1)
    version = models.CharField(max_length=-1)
    up = models.CharField(max_length=1, choices=UP_CHOICES, default=UP_UP)

    class Meta:
        db_table = 'service'
        ordering = ('handler',)

    def __unicode__(self):
        return u'%s, at %s' % (self.handler, self.netbox)

    def get_statistics(self):
        from nav.models.rrd import RrdDataSource

        def average(rds, time_frame):
            from nav.rrd import presenter
            rrd = presenter.presentation()
            rrd.timeLast(time_frame)
            rrd.addDs(rds.id)
            value = rrd.average()
            if not value:
                return None
            else:
                return value[0]

        try:
            data_sources = RrdDataSource.objects.filter(
                rrd_file__key='serviceid', rrd_file__value=self.id)
            data_source_status = data_sources.get(name='STATUS')
            data_source_response_time = data_sources.get(name='RESPONSETIME')
        except RrdDataSource.DoesNotExist:
            return None

        result = {
            'availability': {
                'data_source': data_source_status,
            },
            'response_time': {
                'data_source': data_source_response_time,
            },
        }

        for time_frame in self.TIME_FRAMES:
            # Availability
            value = average(data_source_status, time_frame)
            if value is None or value == 0:
                # average() returns 0 if RRD returns NaN or Error
                value = None
            else:
                value = 100 - (value * 100)
            result['availability'][time_frame] = value

            # Response time
            value = average(data_source_response_time, time_frame)
            if value == 0:
                # average() returns 0 if RRD returns NaN or Error
                value = None
            result['response_time'][time_frame] = value

        return result

class ServiceProperty(models.Model):
    """From MetaNAV: Each service may have an additional set of attributes.
    They are defined here."""

    id = models.IntegerField(primary_key=True) # Serial for faking a primary key
    service = models.ForeignKey(Service, db_column='serviceid')
    property = models.CharField(max_length=64)
    value = models.CharField(max_length=-1)

    class Meta:
        db_table = 'serviceproperty'
        unique_together = (('service', 'property'),) # Primary key

    def __unicode__(self):
        return u'%s=%s, for %s' % (self.property, self.value, self.service)
