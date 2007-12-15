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

from datetime import datetime

from django.db import models

from nav.models.manage import Device, Netbox

# Choices used in multiple models, "imported" into the models which use them
STATE_STATELESS = 'x'
STATE_START = 's'
STATE_END = 'e'
STATE_CHOICES = (
    (STATE_STATELESS, 'stateless'),
    (STATE_START, 'start'),
    (STATE_END, 'end'),
)

class Subsystem(models.Model):
    """From MetaNAV: Defines the subsystems that post or receives an event."""

    name = models.CharField(max_length=-1, primary_key=True)
    description = models.CharField(db_column='descr', max_length=-1)
    class Meta:
        db_table = 'subsystem'

#######################################################################
### Event system

class EventQueue(models.Model):
    """From MetaNAV: The event queue. Additional data in eventqvar. Different
    subsystem (specified in source) post events on the event queue. Normally
    event engine is the target and will take the event off the event queue and
    process it.  getDeviceData are in some cases the target."""

    STATE_STATELESS = STATE_STATELESS
    STATE_START = STATE_START
    STATE_END = STATE_END
    STATE_CHOICES = STATE_CHOICES
    id = models.IntegerField(db_column='eventqid', primary_key=True)
    source = models.ForeignKey('Subsystem', db_column='source',
        related_name='source_of_events')
    target = models.ForeignKey('Subsystem', db_column='target',
        related_name='target_of_events')
    device = models.ForeignKey('Device', db_column='deviceid')
    netbox = models.ForeignKey('Netbox', db_column='netboxid')
    subid = models.CharField(max_length=-1)
    time = models.DateTimeField(default=datetime.now)
    event_type = models.ForeignKey('EventType', db_column='eventtypeid')
    state = models.CharField(max_length=1, choices=STATE_CHOICES,
        default=STATE_STATELESS)
    value = models.IntegerField(default=100)
    severity = models.IntegerField(default=50)
    class Meta:
        db_table = 'eventq'

class EventType(models.Model):
    """From MetaNAV: Defines event types."""

    STATEFUL_TRUE = 'y'
    STATEFUL_FALSE = 'n'
    STATEFUL_CHOICES = (
        (STATEFUL_TRUE, 'stateful'),
        (STATEFUL_FALSE, 'stateless'),
    )
    id = models.CharField(db_column='eventtypeid',
        max_length=32, primary_key=True)
    description = models.CharField(db_column='eventtypedesc', max_length=-1)
    stateful = models.CharField(max_length=1, choices=STATEFUL_CHOICES)
    class Meta:
        db_table = 'eventtype'

class EventQueueVar(models.Model):
    """From MetaNAV: Defines additional (key,value) tuples that follow
    events."""

    event_queue = models.ForeignKey('EventQueue', db_column='eventqid',
        related_name='variables')
    variable = models.CharField(db_column='var', max_length=-1)
    value = models.TextField(db_column='val')
    class Meta:
        db_table = 'eventqvar'
        unique_together = (('event_queue', 'variable'),)

#######################################################################
### Alert system

class AlertQueue(models.Model):
    """From MetaNAV: The alert queue. Additional data in alertqvar and
    alertmsg. Event engine posts alerts on the alert queue (and in addition on
    the alerthist table). Alert engine will process the data on the alert queue
    and send alerts to users based on their alert profiles. When all signed up
    users have received the alert, alert engine will delete the alert from
    alertq (but not from alert history)."""

    STATE_STATELESS = STATE_STATELESS
    STATE_START = STATE_START
    STATE_END = STATE_END
    STATE_CHOICES = STATE_CHOICES
    id = models.IntegerField(db_column='alertqid', primary_key=True)
    source = models.ForeignKey('Subsystem', db_column='source')
    device = models.ForeignKey('Device', db_column='deviceid')
    netbox = models.ForeignKey('Netbox', db_column='netboxid')
    subid = models.CharField(max_length=-1)
    time = models.DateTimeField()
    event_type = models.ForeignKey('EventType', db_column='eventtypeid')
    alert_type = models.ForeignKey('AlertType', db_column='alerttypeid')
    state = models.CharField(max_length=1, choices=STATE_CHOICES,
        default=STATE_STATELESS)
    value = models.IntegerField()
    severity = models.IntegerField()
    class Meta:
        db_table = 'alertq'

class AlertType(models.Model):
    """From MetaNAV: Defines the alert types. An event type may have many alert
    types."""

    id = models.IntegerField(db_column='alerttypeid', primary_key=True)
    event_type = models.ForeignKey('EventType', db_column='eventtypeid')
    name = models.CharField(db_column='alterttype', max_length=-1)
    description= models.CharField(db_column='alerttypedesc', max_length=-1)
    class Meta:
        db_table = 'alerttype'
        unique_together = (('event_type', 'name'),)

class AlertQueueMessage(models.Model):
    """From MetaNAV: Event engine will, based on alertmsg.conf, preformat the
    alarm messages, one message for each configured alert channel (email, sms),
    one message for each configured language. The data are stored in the
    alertmsg table."""

    alert_queue = models.ForeignKey('AlertQueue', db_column='alertqid',
        related_name='messages')
    type = models.CharField(db_column='msgtype', max_length=-1)
    language = models.CharField(max_length=-1)
    message = models.TextField(db_column='msg')
    class Meta:
        db_table = 'alertqmsg'
        unique_together = (('alert_queue', 'type', 'language'),)

class AlertQueueVariable(models.Model):
    """From MetaNAV: Defines additional (key,value) tuples that follow alert.
    Note: the eventqvar tuples are passed along to the alertqvar table so that
    the variables may be used in alert profiles."""

    alert_queue = models.ForeignKey('AlertQueue', db_column='alertqid',
        related_name='variables')
    variable = models.CharField(db_column='var', max_length=-1)
    value = models.TextField(db_column='val')
    class Meta:
        db_table = 'alertqvar'
        unique_together = (('alert_queue', 'variable'),)

class AlertHistory(models.Model):
    """From MetaNAV: The alert history. Simular to the alert queue with one
    important distinction; alert history stores statefull events as one row,
    with the start and end time of the event."""

    id = models.IntegerField(db_column='alerthistid', primary_key=True)
    source = models.ForeignKey('Subsystem', db_column='source')
    device = models.ForeignKey('Device', db_column='deviceid')
    netbox = models.ForeignKey('Netbox', db_column='netboxid')
    subid = models.CharField(max_length=-1)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    event_type = models.ForeignKey('EventType', db_column='eventtypeid')
    alert_type = models.ForeignKey('AlertType', db_column='alerttypeid')
    value = models.IntegerField()
    severity = models.IntegerField()
    class Meta:
        db_table = 'alerthist'

class AlertHistoryMessage(models.Model):
    """From MetaNAV: To have a history of the formatted messages too, they are
    stored in alerthistmsg."""

    STATE_STATELESS = STATE_STATELESS
    STATE_START = STATE_START
    STATE_END = STATE_END
    STATE_CHOICES = STATE_CHOICES
    alert_history = models.ForeignKey('AlertHistory', db_column='alerthistid',
        related_name='messages')
    state = models.CharField(max_length=1, choices=STATE_CHOICES,
        default=STATE_STATELESS)
    type = models.CharField(db_column='msgtype', max_length=-1)
    language = models.CharField(max_length=-1)
    message = models.TextField(db_column='msg')
    class Meta:
        db_table = 'alerthistmsg'
        unique_together = (('alert_history', 'state', 'type', 'language'),)

class AlertHistoryVariable(models.Model):
    """From MetaNAV: Defines additional (key,value) tuples that follow the
    alerthist record."""

    STATE_STATELESS = STATE_STATELESS
    STATE_START = STATE_START
    STATE_END = STATE_END
    STATE_CHOICES = STATE_CHOICES
    alert_history = models.ForeignKey('AlertHistory', db_column='alerthistid')
    state = models.CharField(max_length=1, choices=STATE_CHOICES,
        default=STATE_STATELESS)
    variable = models.CharField(db_column='var', max_length=-1)
    value = models.TextField(db_column='val')
    class Meta:
        db_table = 'alerthistvar'
        unique_together = (('alert_history', 'state', 'variable'),)

class AlertEngine(models.Model):
    """From MetaNAV: Used by alert engine to keep track of processed alerts."""

    last_alert_queue_id = models.IntegerField(db_column='lastalertqueueid')
    class Meta:
        db_table = 'alertengine'
