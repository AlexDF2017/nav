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

"""Django ORM wrapper for the NAV manage database"""

__copyright__ = "Copyright 2007-2008 UNINETT AS"
__license__ = "GPL"
__author__ = "Stein Magnus Jodal (stein.magnus.jodal@uninett.no)"
__id__ = "$Id$"

from datetime import datetime, timedelta
import time

from django.core.urlresolvers import reverse
from django.db import models

import nav.natsort
import nav.util

# Choices used in multiple models, "imported" into the models which use them
LINK_UP = 'y'
LINK_DOWN = 'n'
LINK_DOWN_ADM = 'd'
LINK_CHOICES = (
    (LINK_UP, 'up'), # In old devBrowser: 'Active'
    (LINK_DOWN, 'down (operDown)'), # In old devBrowser: 'Not active'
    (LINK_DOWN_ADM, 'down (admDown)'), # In old devBrowser: 'Denied'
)

#######################################################################
### Model helper functions

def to_ifname_style(interface):
    """Filter interface names from ifDescr to ifName style"""

    filters = (
        ('Vlan', 'Vl'),
        ('TenGigabitEthernet', 'Te'),
        ('GigabitEthernet', 'Gi'),
        ('FastEthernet', 'Fa'),
        ('Ethernet', 'Et'),
        ('Loopback', 'Lo'),
        ('Tunnel', 'Tun'),
        ('Serial', 'Se'),
        ('Dialer', 'Di'),
        ('-802.1Q vLAN subif', ''),
        ('-ISL vLAN subif', ''),
        ('-aal5 layer', ''),
    )
    for old, new in filters:
        interface = interface.replace(old, new)
    return interface

#######################################################################
### Netbox-related models

class Netbox(models.Model):
    """From MetaNAV: The netbox table is the heart of the heart so to speak,
    the most central table of them all. The netbox tables contains information
    on all IP devices that NAV manages with adhering information and
    relations."""

    UP_UP = 'y'
    UP_DOWN = 'n'
    UP_SHADOW = 's'
    UP_CHOICES = (
        (UP_UP, 'up'),
        (UP_DOWN, 'down'),
        (UP_SHADOW, 'shadow'),
    )
    TIME_FRAMES = ('day', 'week', 'month')

    id = models.AutoField(db_column='netboxid', primary_key=True)
    ip = models.IPAddressField(unique=True)
    room = models.ForeignKey('Room', db_column='roomid')
    type = models.ForeignKey('NetboxType', db_column='typeid', null=True)
    device = models.ForeignKey('Device', db_column='deviceid')
    sysname = models.CharField(unique=True, max_length=-1)
    category = models.ForeignKey('Category', db_column='catid')
    # TODO: Probably deprecated. Check and remove.
    #subcategory = models.CharField(db_column='subcat', max_length=-1)
    organization = models.ForeignKey('Organization', db_column='orgid')
    read_only = models.CharField(db_column='ro', max_length=-1)
    read_write = models.CharField(db_column='rw', max_length=-1)
    prefix = models.ForeignKey('Prefix', db_column='prefixid', null=True)
    up = models.CharField(max_length=1, choices=UP_CHOICES, default=UP_UP)
    snmp_version = models.IntegerField()
    snmp_agent = models.CharField(max_length=-1)
    up_since = models.DateTimeField(db_column='upsince')
    up_to_date = models.BooleanField(db_column='uptodate')
    discovered = models.DateTimeField()

    class Meta:
        db_table = 'netbox'
        ordering = ('sysname',)

    def __unicode__(self):
        return self.sysname

    def get_absolute_url(self):
        kwargs={
            'name': self.sysname,
        }
        return reverse('ipdevinfo-details-by-name', kwargs=kwargs)

    def last_updated(self):
        try:
            value = self.info_set.get(variable='lastUpdated').value
            value = int(value) / 1000.0
            return datetime(*time.gmtime(value)[:6])
        except NetboxInfo.DoesNotExist:
            return None
        except ValueError:
            return '(Invalid value in DB)'

    def get_gwports(self):
        return GwPort.objects.filter(module__netbox=self)

    def get_swports(self):
        return SwPort.objects.filter(module__netbox=self)

    def get_availability(self):
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
                rrd_file__subsystem='pping', rrd_file__netbox=self)
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

    def get_uplinks(self):
        result = []

        for swport in self.connected_to_swport.all():
            if swport.swportvlan_set.filter(
                direction=SwPortVlan.DIRECTION_DOWN).count():
                result.append(swport)

        for gwport in self.connected_to_gwport.all():
            result.append(gwport)

        return result

class NetboxInfo(models.Model):
    """From MetaNAV: The netboxinfo table is the place to store additional info
    on a netbox."""

    id = models.AutoField(db_column='netboxinfoid', primary_key=True)
    netbox = models.ForeignKey('Netbox', db_column='netboxid',
        related_name='info_set')
    key = models.CharField(max_length=-1)
    variable = models.CharField(db_column='var', max_length=-1)
    value = models.TextField(db_column='val')

    class Meta:
        db_table = 'netboxinfo'
        unique_together = (('netbox', 'key', 'variable', 'value'),)

    def __unicode__(self):
        return u'%s="%s"' % (self.variable, self.value)

class Device(models.Model):
    """From MetaNAV: The device table contains all physical devices in the
    network. As opposed to the netbox table, the device table focuses on the
    physical box with its serial number. The device may appear as different net
    boxes or may appear in different modules throughout its lifetime."""

    id = models.AutoField(db_column='deviceid', primary_key=True)
    product = models.ForeignKey('Product', db_column='productid', null=True)
    serial = models.CharField(unique=True, max_length=-1)
    hardware_version = models.CharField(db_column='hw_ver', max_length=-1)
    firmware_version = models.CharField(db_column='fw_ver', max_length=-1)
    software_version = models.CharField(db_column='sw_ver', max_length=-1)
    auto = models.BooleanField(default=False)
    active = models.BooleanField(default=False)
    device_order = models.ForeignKey('DeviceOrder', db_column='deviceorderid',
        null=True)
    discovered = models.DateTimeField(default=datetime.now)

    class Meta:
        db_table = 'device'

    def __unicode__(self):
        return self.serial

class Module(models.Model):
    """From MetaNAV: The module table defines modules. A module is a part of a
    netbox of category GW, SW and GSW. A module has ports; i.e router ports
    and/or switch ports. A module is also a physical device with a serial
    number."""

    UP_UP = 'y'
    UP_DOWN = 'n'
    UP_CHOICES = (
        (UP_UP, 'up'),
        (UP_DOWN, 'down'),
    )

    id = models.AutoField(db_column='moduleid', primary_key=True)
    device = models.ForeignKey('Device', db_column='deviceid')
    netbox = models.ForeignKey('Netbox', db_column='netboxid')
    module_number = models.IntegerField(db_column='module')
    model = models.CharField(max_length=-1)
    description = models.CharField(db_column='descr', max_length=-1)
    up = models.CharField(max_length=1, choices=UP_CHOICES, default=UP_UP)
    down_since = models.DateTimeField(db_column='downsince')

    class Meta:
        db_table = 'module'
        ordering = ('netbox', 'module_number')
        unique_together = (('netbox', 'module_number'),)

    def __unicode__(self):
        return u'%d, at %s' % (self.module_number, self.netbox)

    def get_absolute_url(self):
        kwargs={
            'netbox_sysname': self.netbox.sysname,
            'module_number': self.module_number,
        }
        return reverse('ipdevinfo-module-details', kwargs=kwargs)

    def get_gwports(self):
        return GwPort.objects.select_related(depth=2).filter(module=self)

    def get_gwports_sorted(self):
        """Returns gwports naturally sorted by interface name"""

        ports = self.get_gwports()
        interface_names = [p.interface for p in ports]
        unsorted = dict(zip(interface_names, ports))
        interface_names.sort(key=nav.natsort.split)
        sorted_ports = [unsorted[i] for i in interface_names]
        return sorted_ports

    def get_swports(self):
        return SwPort.objects.select_related(depth=2).filter(module=self)

    def get_swports_sorted(self):
        """Returns swports naturally sorted by interface name"""

        ports = self.get_swports()
        interface_names = [p.interface for p in ports]
        unsorted = dict(zip(interface_names, ports))
        interface_names.sort(key=nav.natsort.split)
        sorted_ports = [unsorted[i] for i in interface_names]
        return sorted_ports

class Memory(models.Model):
    """From MetaNAV: The mem table describes the memory (memory and nvram) of a
    netbox."""

    id = models.AutoField(db_column='memid', primary_key=True)
    netbox = models.ForeignKey('Netbox', db_column='netboxid')
    type = models.CharField(db_column='memtype', max_length=-1)
    device = models.CharField(max_length=-1)
    size = models.IntegerField()
    used = models.IntegerField()

    class Meta:
        db_table = 'mem'
        unique_together = (('netbox', 'type', 'device'),)

    def __unicode__(self):
        if self.used is not None and self.size is not None and self.size != 0:
            return u'%s, %d%% used' % (self.type, self.used * 100 // self.size)
        else:
            return self.type

class Room(models.Model):
    """From MetaNAV: The room table defines a wiring closes / network room /
    server room."""

    id = models.CharField(db_column='roomid', max_length=30, primary_key=True)
    location = models.ForeignKey('Location', db_column='locationid')
    description = models.CharField(db_column='descr', max_length=-1)
    optional_1 = models.CharField(db_column='opt1', max_length=-1)
    optional_2 = models.CharField(db_column='opt2', max_length=-1)
    optional_3 = models.CharField(db_column='opt3', max_length=-1)
    optional_4 = models.CharField(db_column='opt4', max_length=-1)

    class Meta:
        db_table = 'room'

    def __unicode__(self):
        return u'%s (%s, %s)' % (self.id, self.description, self.location)

class Location(models.Model):
    """From MetaNAV: The location table defines a group of rooms; i.e. a
    campus."""

    id = models.CharField(db_column='locationid',
        max_length=30, primary_key=True)
    description = models.CharField(db_column='descr', max_length=-1)

    class Meta:
        db_table = 'location'

    def __unicode__(self):
        return self.description

class Organization(models.Model):
    """From MetaNAV: The org table defines an organization which is in charge
    of a given netbox and is the user of a given prefix."""

    id = models.CharField(db_column='orgid', max_length=30, primary_key=True)
    parent = models.ForeignKey('self', db_column='parent', null=True)
    description = models.CharField(db_column='descr', max_length=-1)
    optional_1 = models.CharField(db_column='opt1', max_length=-1)
    optional_2 = models.CharField(db_column='opt2', max_length=-1)
    optional_3 = models.CharField(db_column='opt3', max_length=-1)

    class Meta:
        db_table = 'org'

    def __unicode__(self):
        return u'%s (%s)' % (self.id, self.description)

class Category(models.Model):
    """From MetaNAV: The cat table defines the categories of a netbox
    (GW,GSW,SW,EDGE,WLAN,SRV,OTHER)."""

    id = models.CharField(db_column='catid', max_length=8, primary_key=True)
    description = models.CharField(db_column='descr', max_length=-1)
    req_snmp = models.BooleanField()

    class Meta:
        db_table = 'cat'

    def __unicode__(self):
        return u'%s (%s)' % (self.id, self.description)

class Subcategory(models.Model):
    """From MetaNAV: The subcat table defines subcategories within a category.
    A category may have many subcategories. A subcategory belong to one and
    only one category."""

    id = models.CharField(db_column='subcatid', max_length=-1, primary_key=True)
    description = models.CharField(db_column='descr', max_length=-1)
    category = models.ForeignKey('Category', db_column='catid')

    class Meta:
        db_table = 'subcat'

    def __unicode__(self):
        try:
            return u'%s, sub of %s' % (self.description, self.category)
        except Category.DoesNotExist:
            return self.description

class NetboxCategory(models.Model):
    """From MetaNAV: A netbox may be in many subcategories. This relation is
    defined here."""

    # TODO: This should be a ManyToMany-field in Netbox, but at this time
    # Django only supports specifying the name of the M2M-table, and not the
    # column names.
    id = models.AutoField(primary_key=True) # Serial for faking a primary key
    netbox = models.ForeignKey('Netbox', db_column='netboxid')
    category = models.ForeignKey('Subcategory', db_column='category')

    class Meta:
        db_table = 'netboxcategory'
        unique_together = (('netbox', 'category'),) # Primary key

    def __unicode__(self):
        return u'%s in category %s' % (self.netbox, self.category)

class NetboxType(models.Model):
    """From MetaNAV: The type table defines the type of a netbox, the
    sysobjectid being the unique identifier."""

    id = models.AutoField(db_column='typeid', primary_key=True)
    vendor = models.ForeignKey('Vendor', db_column='vendorid')
    name = models.CharField(db_column='typename', max_length=-1)
    sysobject = models.CharField(db_column='sysobjectid',
        unique=True, max_length=-1)
    cdp = models.BooleanField(default=False)
    tftp = models.BooleanField(default=False)
    cs_at_vlan = models.BooleanField()
    chassis = models.BooleanField(default=True)
    frequency = models.IntegerField()
    description = models.CharField(db_column='descr', max_length=-1)

    class Meta:
        db_table = 'type'
        unique_together = (('vendor', 'name'),)

    def __unicode__(self):
        return u'%s (%s, from %s)' % (self.name, self.description, self.vendor)

#######################################################################
### Device management

class Vendor(models.Model):
    """From MetaNAV: The vendor table defines vendors. A type is of a vendor. A
    product is of a vendor."""

    id = models.CharField(db_column='vendorid', max_length=15, primary_key=True)
    enterprise_id = models.IntegerField(db_column='enterpriseid')

    class Meta:
        db_table = 'vendor'

    def __unicode__(self):
        return self.id

class Product(models.Model):
    """From MetaNAV: The product table is used be Device Management to register
    products. A product has a product number and is of a vendor."""

    id = models.AutoField(db_column='productid', primary_key=True)
    vendor = models.ForeignKey('Vendor', db_column='vendorid')
    product_number = models.CharField(db_column='productno', max_length=-1)
    description = models.CharField(db_column='descr', max_length=-1)

    class Meta:
        db_table = 'product'
        unique_together = (('vendor', 'product_number'),)

    def __unicode__(self):
        return u'%s (%s), from vendor %s' % (
            self.description, self.product_number, self.vendor)

class DeviceOrder(models.Model):
    """From MetaNAV: The deviceorder table is used by Device Management to
    place orders. Not compulsary. An order consists of a set of devices (on or
    more) of a certain product."""

    id = models.AutoField(db_column='deviceorderid', primary_key=True)
    registered = models.DateTimeField(default=datetime.now)
    ordered = models.DateField()
    arrived = models.DateTimeField()
    order_number = models.CharField(db_column='ordernumber', max_length=-1)
    comment = models.CharField(max_length=-1)
    retailer = models.CharField(max_length=-1)
    username = models.CharField(max_length=-1)
    organization = models.ForeignKey('Organization', db_column='orgid')
    product = models.ForeignKey('Product', db_column='productid')
    updated_by = models.CharField(db_column='updatedby', max_length=-1)
    last_updated = models.DateField(db_column='lastupdated')

    class Meta:
        db_table = 'deviceorder'

    def __unicode__(self):
        return self.order_number

#######################################################################
### Router/topology

class GwPort(models.Model):
    """From MetaNAV: The gwport table defines the router ports connected to a
    module. Only router ports that are not shutdown are included. Router ports
    without defined IP addresses are also excluded."""

    LINK_UP = LINK_UP
    LINK_DOWN = LINK_DOWN
    LINK_DOWN_ADM = LINK_DOWN_ADM
    LINK_CHOICES = LINK_CHOICES

    id = models.AutoField(db_column='gwportid', primary_key=True)
    module = models.ForeignKey('Module', db_column='moduleid')
    ifindex = models.IntegerField()
    link = models.CharField(max_length=1, choices=LINK_CHOICES)
    master_index = models.IntegerField(db_column='masterindex')
    interface = models.CharField(max_length=-1)
    speed = models.FloatField()
    metric = models.IntegerField()
    to_netbox = models.ForeignKey('Netbox', db_column='to_netboxid', null=True,
        related_name='connected_to_gwport')
    to_swport = models.ForeignKey('SwPort', db_column='to_swportid', null=True,
        related_name='connected_to_gwport')
    port_name = models.CharField(db_column='portname', max_length=-1)

    class Meta:
        db_table = 'gwport'
        ordering = ('module', 'interface')
        unique_together = (('module', 'ifindex'),)

    def __unicode__(self):
        name = self.interface or self.ifindex
        return u'%s, at module %s' % (name, self.module)

    def get_absolute_url(self):
        kwargs={
            'netbox_sysname': self.module.netbox.sysname,
            'module_number': self.module.module_number,
            'port_id': self.id,
        }
        return reverse('ipdevinfo-gwport-details', kwargs=kwargs)

    def get_interface_display(self):
        return to_ifname_style(self.interface)

    def get_status_classes(self):
        """Status classes for IP Device Info port view"""

        classes = ['port']
        if self.speed:
            classes.append('Mb%d' % self.speed)
        return ' '.join(classes)

    def get_status_title(self):
        """Status title for IP Device Info port view"""

        title = []
        if self.interface:
            title.append(self.interface)
        if self.speed:
            title.append('%d Mbit' % self.speed)
        try:
            title.append('-> %s' % self.to_netbox)
        except Netbox.DoesNotExist:
            pass
        if self.port_name:
            title.append(self.port_name)
        return ', '.join(title)

class GwPortPrefix(models.Model):
    """From MetaNAV: The gwportprefix table defines the router port IP
    addresses, one or more. HSRP is also supported."""

    gwport = models.ForeignKey('GwPort', db_column='gwportid')
    prefix = models.ForeignKey('Prefix', db_column='prefixid')
    gw_ip = models.IPAddressField(db_column='gwip', primary_key=True)
    hsrp = models.BooleanField(default=False)

    class Meta:
        db_table = 'gwportprefix'

    def __unicode__(self):
        return self.gw_ip

class Prefix(models.Model):
    """From MetaNAV: The prefix table stores IP prefixes."""

    id = models.AutoField(db_column='prefixid', primary_key=True)
    # TODO: Create CIDRField in Django
    net_address = models.TextField(db_column='netaddr', unique=True)
    vlan = models.ForeignKey('Vlan', db_column='vlanid', null=True)

    class Meta:
        db_table = 'prefix'

    def __unicode__(self):
        return u'%s at vlan %s' % (self.net_address, self.vlan)

class Vlan(models.Model):
    """From MetaNAV: The vlan table defines the IP broadcast domain / vlan. A
    broadcast domain often has a vlan value, it may consist of many IP
    prefixes, it is of a network type, it is used by an organization (org) and
    has a user group (usage) within the org."""

    id = models.AutoField(db_column='vlanid', primary_key=True)
    vlan = models.IntegerField()
    net_type = models.ForeignKey('NetType', db_column='nettype')
    organization = models.ForeignKey('Organization', db_column='orgid',
        null=True)
    usage = models.ForeignKey('Usage', db_column='usageid', null=True)
    net_ident = models.CharField(db_column='netident', max_length=-1)
    description = models.CharField(max_length=-1)

    class Meta:
        db_table = 'vlan'

    def __unicode__(self):
        vlan = str(self.vlan) or 'unknown'
        try:
            return u'%s, type %s, ident %s' % (
                vlan, self.net_type, self.net_ident)
        except NetType.DoesNotExist:
            return u'%s, ident %s' % (vlan, self.net_ident)

class NetType(models.Model):
    """From MetaNAV: The nettype table defines network type;lan, core, link,
    elink, loopback, closed, static, reserved, scope. The network types are
    predefined in NAV and may not be altered."""

    id = models.CharField(db_column='nettypeid',
        max_length=-1, primary_key=True)
    description = models.CharField(db_column='descr', max_length=-1)
    edit = models.BooleanField(default=False)

    class Meta:
        db_table = 'nettype'

    def __unicode__(self):
        return self.id

class Usage(models.Model):
    """From MetaNAV: The usage table defines the user group (student, staff
    etc). Usage categories are maintained in the edit database tool."""

    id = models.CharField(db_column='usageid',
        max_length=30, primary_key=True)
    description = models.CharField(db_column='descr', max_length=-1)

    class Meta:
        db_table = 'usage'

    def __unicode__(self):
        return u'%s (%s)' % (self.id, self.description)

class Arp(models.Model):
    """From MetaNAV: The arp table contains (ip, mac, time start, time end)."""

    id = models.AutoField(db_column='arpid', primary_key=True)
    netbox = models.ForeignKey('Netbox', db_column='netboxid')
    prefix = models.ForeignKey('Prefix', db_column='prefixid', null=True)
    sysname = models.CharField(max_length=-1)
    ip = models.IPAddressField()
    # TODO: Create MACAddressField in Django
    mac = models.CharField(max_length=17)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    class Meta:
        db_table = 'arp'

    def __unicode__(self):
        return u'%s to %s' % (self.ip, self.mac)

#######################################################################
### Switch/topology

class SwPort(models.Model):
    """From MetaNAV: The swport table defines the switchports connected to a
    module."""

    LINK_UP = LINK_UP
    LINK_DOWN = LINK_DOWN
    LINK_DOWN_ADM = LINK_DOWN_ADM
    LINK_CHOICES = LINK_CHOICES
    DUPLEX_FULL = 'f'
    DUPLEX_HALF = 'h'
    DUPLEX_CHOICES = (
        (DUPLEX_FULL, 'full duplex'),
        (DUPLEX_HALF, 'half duplex'),
    )

    id = models.AutoField(db_column='swportid', primary_key=True)
    module = models.ForeignKey('Module', db_column='moduleid')
    ifindex = models.IntegerField()
    port = models.IntegerField()
    interface = models.CharField(max_length=-1)
    link = models.CharField(max_length=1, choices=LINK_CHOICES)
    speed = models.FloatField()
    duplex = models.CharField(max_length=1, choices=DUPLEX_CHOICES)
    media = models.CharField(max_length=-1)
    vlan = models.IntegerField()
    trunk = models.BooleanField()
    port_name = models.CharField(db_column='portname', max_length=-1)
    to_netbox = models.ForeignKey('Netbox', db_column='to_netboxid', null=True,
        related_name='connected_to_swport')
    to_swport = models.ForeignKey('self', db_column='to_swportid', null=True,
        related_name='connected_to_swport')

    class Meta:
        db_table = 'swport'
        ordering = ('module', 'interface')
        unique_together = (('module', 'ifindex'),)

    def __unicode__(self):
        name = self.interface or self.ifindex or self.port
        return u'%s, at module %s' % (name, self.module)

    def get_absolute_url(self):
        kwargs={
            'netbox_sysname': self.module.netbox.sysname,
            'module_number': self.module.module_number,
            'port_id': self.id,
        }
        return reverse('ipdevinfo-swport-details', kwargs=kwargs)

    def get_interface_display(self):
        return to_ifname_style(self.interface)

    def get_status_classes(self):
        """Status classes for IP Device Info port view"""

        classes = ['port']
        if self.link == self.LINK_UP and self.speed:
            classes.append('Mb%d' % self.speed)
        if self.link == self.LINK_DOWN_ADM:
            classes.append('disabled')
        elif self.link != self.LINK_UP:
            classes.append('passive')
        if self.trunk:
            classes.append('trunk')
        if self.duplex:
            classes.append('%sduplex' % self.duplex)
        # XXX: This causes a DB query per port
        if self.swportblocked_set.count():
            classes.append('blocked')
        return ' '.join(classes)

    def get_status_title(self):
        """Status title for IP Device Info port view"""

        title = []
        if self.interface:
            title.append(self.interface)
        if self.link == self.LINK_UP and self.speed:
            title.append('%d Mbit' % self.speed)
        try:
            title.append('-> %s' % self.to_netbox)
        except Netbox.DoesNotExist:
            pass
        if self.link == self.LINK_DOWN_ADM:
            title.append('disabled')
        elif self.link != self.LINK_UP:
            title.append('not active')
        if self.trunk:
            title.append('trunk')
        if self.duplex:
            title.append(self.get_duplex_display())
        if self.media:
            title.append(self.media)

        # XXX: This causes a DB query per port
        vlans = [str(swpv.vlan.vlan)
            for swpv in self.swportvlan_set.select_related(depth=1)]
        if vlans:
            title.append('vlan ' + ','.join(vlans))

        # XXX: This causes a DB query per port
        blocked_vlans = [str(block.vlan)
            for block in self.swportblocked_set.select_related(depth=1)]
        if blocked_vlans:
            title.append('blocked ' + ','.join(blocked_vlans))

        return ', '.join(title)

    def get_active_time(self, interval=30):
        """
        Time since last CAM activity on port, looking at CAM entries
        for the last ``interval'' (default 30) days.

        Returns None if no activity is found, else number of days since last
        activity as a datetime.timedelta object.
        """

        if hasattr(self, 'time_since_activity'):
            return self.time_since_activity

        min_time = datetime.now() - timedelta(interval)
        try:
            # XXX: This causes a DB query per port
            # Use .values() to avoid creating additional objects we do not need
            last_cam_entry_end_time = self.module.netbox.cam_set.filter(
                ifindex=self.ifindex, end_time__gt=min_time).order_by(
                'end_time').values('end_time')[0]['end_time']
        except (Cam.DoesNotExist, IndexError):
            # Inactive/not in use
            return None

        if last_cam_entry_end_time == datetime.max:
            # Active now
            self.time_since_activity = timedelta(0)
        else:
            # Active some time inside the given interval
            self.time_since_activity = datetime.now() - last_cam_entry_end_time

        return self.time_since_activity

    def get_active_classes(self, interval=30):
        """Active classes for IP Device Info port view"""

        classes = ['port']

        if self.link == self.LINK_UP:
            classes.append('active')
            classes.append('link')
        else:
            active = self.get_active_time(interval)
            if active is not None:
                classes.append('active')
            else:
                classes.append('inactive')

        return ' '.join(classes)

    def get_active_style(self, interval=30):
        """Active style for IP Device Info port view"""

        # Color range for port activity tab
        color_recent = (116, 196, 118)
        color_longago = (229, 245, 224)
        # XXX: Is this CPU intensive? Cache result?
        gradient = nav.util.color_gradient(
            color_recent, color_longago, interval)

        style = ''

        if self.link == self.LINK_UP:
            style = 'background-color: #%s;' % nav.util.colortohex(
                gradient[0])
        else:
            active = self.get_active_time(interval)
            if active is not None:
                style = 'background-color: #%s;' % nav.util.colortohex(
                    gradient[active.days])

        return style

    def get_active_title(self, interval=30):
        """Active title for IP Device Info port view"""

        title = []

        if self.interface:
            title.append(self.interface)

        if self.link == self.LINK_UP:
            title.append('link now')
        else:
            active = self.get_active_time(interval)
            if active is not None:
                if active.days > 1:
                    title.append('MAC seen %d days ago' % active.days)
                elif active.days == 1:
                    title.append('MAC seen 1 day ago')
                else:
                    title.append('MAC seen today')
            else:
                title.append('free')

        return ', '.join(title)

class SwPortVlan(models.Model):
    """From MetaNAV: The swportvlan table defines the vlan values on all switch
    ports. dot1q trunk ports typically have several rows in this table."""

    DIRECTION_UNDEFINED = 'x'
    DIRECTION_UP = 'o'
    DIRECTION_DOWN = 'n'
    DIRECTION_CHOICES = (
        (DIRECTION_UNDEFINED, 'undefined'),
        (DIRECTION_UP, 'up'),
        (DIRECTION_DOWN, 'down'),
    )

    id = models.AutoField(db_column='swportvlanid', primary_key=True)
    swport = models.ForeignKey('SwPort', db_column='swportid')
    vlan = models.ForeignKey('Vlan', db_column='vlanid')
    direction = models.CharField(max_length=1, choices=DIRECTION_CHOICES,
        default=DIRECTION_UNDEFINED)

    class Meta:
        db_table = 'swportvlan'
        unique_together = (('swport', 'vlan'),)

    def __unicode__(self):
        return u'%s, on vlan %s' % (self.swport, self.vlan)

class SwPortAllowedVlan(models.Model):
    """From MetaNAV: Stores a hexstring that has “hidden” information about the
    vlans that are allowed to traverse a given trunk."""

    swport = models.ForeignKey('SwPort', db_column='swportid', primary_key=True)
    hex_string = models.CharField(db_column='hexstring', max_length=-1)

    class Meta:
        db_table = 'swportallowedvlan'

    def __unicode__(self):
        return u'Allowed vlan for swport %s' % self.swport

class SwPortBlocked(models.Model):
    """From MetaNAV: This table defines the spanning tree blocked ports for a
    given vlan for a given switch port."""

    swport = models.ForeignKey('SwPort', db_column='swportid', primary_key=True)
    # XXX: 'vlan' is not a foreignkey to the vlan table in the database, but
    # it should maybe be a foreign key.
    vlan = models.IntegerField()

    class Meta:
        db_table = 'swportblocked'
        unique_together = (('swport', 'vlan'),) # Primary key

    def __unicode__(self):
        return '%d, at swport %s' % (self.vlan, self.swport)

class SwPortToNetbox(models.Model):
    """From MetaNAV: A help table used in the process of building the physical
    topology of the network. swp_netbox defines the candidates for next hop
    physical neighborship."""

    id = models.AutoField(db_column='swp_netboxid', primary_key=True)
    netbox = models.ForeignKey('Netbox', db_column='netboxid')
    ifindex = models.IntegerField()
    to_netbox = models.ForeignKey('Netbox', db_column='to_netboxid',
        related_name='candidate_for_next_hop_set')
    to_swport = models.ForeignKey('SwPort', db_column='to_swportid', null=True,
        related_name='candidate_for_next_hop_set')
    miss_count = models.IntegerField(db_column='misscnt', default=0)

    class Meta:
        db_table = 'swp_netbox'
        unique_together = (('netbox', 'ifindex', 'to_netbox'),)

    def __unicode__(self):
        return u'%d, %s' % (self.ifindex, self.netbox)

class NetboxVtpVlan(models.Model):
    """From MetaNAV: A help table that contains the vtp vlan database of a
    switch. For certain cisco switches cam information is gathered using a
    community@vlan string. It is then necessary to know all vlans that are
    active on a switch. The vtp vlan table is an extra source of
    information."""

    id = models.AutoField(primary_key=True) # Serial for faking a primary key
    netbox = models.ForeignKey('Netbox', db_column='netboxid')
    vtp_vlan = models.IntegerField(db_column='vtpvlan')

    class Meta:
        db_table = 'netbox_vtpvlan'
        unique_together = (('netbox', 'vtp_vlan'),)

    def __unicode__(self):
        return u'%d, at %s' % (self.vtp_vlan, self.netbox)

class Cam(models.Model):
    """From MetaNAV: The cam table defines (swport, mac, time start, time
    end)"""

    id = models.AutoField(db_column='camid', primary_key=True)
    netbox = models.ForeignKey('Netbox', db_column='netboxid', null=True)
    sysname = models.CharField(max_length=-1)
    ifindex = models.IntegerField()
    module = models.CharField(max_length=4)
    port = models.CharField(max_length=-1)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    miss_count = models.IntegerField(db_column='misscnt', default=0)
    # TODO: Create MACAddressField in Django
    mac = models.CharField(max_length=17)

    class Meta:
        db_table = 'cam'
        unique_together = (('netbox', 'sysname', 'module', 'port',
                            'mac', 'start_time'),)

    def __unicode__(self):
        return u'%s, %s' % (self.mac, self.netbox)
