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
# Authors: Thomas Adamcik <thomas.adamcik@uninett.no>
#

"""Django ORM wrapper for profiles in NAV"""

__copyright__ = "Copyright 2007-2008 UNINETT AS"
__license__ = "GPL"
__author__ = "Thomas Adamcik (thomas.adamcik@uninett.no"
__id__ = "$Id$"

import logging
import os
import sys
import traceback
from datetime import datetime
import md5

from django.db import models
from django.db.models import Q

import nav.path
import nav.pwhash
from nav.db.navprofiles import Account as OldAccount
from nav.auth import hasPrivilege
from nav.config import getconfig as get_alertengine_config
from nav.alertengine.dispatchers import DISPATCHERS, DISPATCHER_TYPES, DispatcherException

from nav.models.event import AlertQueue, AlertType, EventType, Subsystem
from nav.models.manage import Arp, Cam, Category, Device, GwPort, Location, \
    Memory, Netbox, NetboxInfo, NetboxType, Organization, Prefix, Product, \
    Room, Subcategory, SwPort, Usage, Vlan, Vendor

logger = logging.getLogger('nav.alertengine')

configfile = os.path.join(nav.path.sysconfdir, 'alertengine.conf')

# This should be the authorative source as to which models alertengine supports.
# The acctuall mapping from alerts to data in these models is done the MatchField
# model.
SUPPORTED_MODELS = [
    # event models
        AlertQueue, AlertType, EventType,
    # manage models
        Arp, Cam, Category, Device, GwPort, Location, Memory, Netbox, NetboxInfo,
        NetboxType, Organization, Prefix, Product, Room, Subcategory, SwPort,
        Vendor, Vlan,
        Usage,
]

_ = lambda a: a

#######################################################################
### Account models

class Account(models.Model):
    ''' NAV's basic account model'''

    login = models.CharField(unique=True)
    name = models.CharField()
    password = models.CharField()
    ext_sync = models.CharField()

    class Meta:
        db_table = u'account'
        ordering = ('login',)

    def __unicode__(self):
        return self.login

    def get_active_profile(self):
        '''Returns the accounts active alert profile'''
        return self.alertpreference.active_profile

    def has_perm(self, action, target):
        '''Checks user permisions by using legacy NAV hasPrivilege function'''

        # Simply wrap the hasPrivilege function of non-Django nav.
        account = OldAccount.loadByLogin(str(self.login))
        return hasPrivilege(account, action, target)

    def set_password(self, password):
        '''Sets user password. Copied from nav.db.navprofiles'''
        if len(password.strip()):
            hash = nav.pwhash.Hash(password=password)
            self.password = str(hash)
        else:
            self.password = ''

    def check_password(self, password):
        """
        Return True if the submitted authentication tokens are valid
        for this Account.  In simpler terms; when password
        authentication is used, this method compares the given
        password with the one stored for this account and returns true
        if they are equal.  If the stored password is blank, we
        interpret this as: 'The user is not allowed to log in'

        In the future, this could be extended to accept other types of
        authentication tokens, such as personal certificates or
        whatever.

        Copied from nav.db.navprofiles
        """
        if len(self.password.strip()) > 0:
            stored_hash = nav.pwhash.Hash()
            try:
                stored_hash.set_hash(self.password)
            except nav.pwhash.InvalidHashStringError:
                # Probably an old style NAV password hash, get out
                # of here and check it the old way
                pass
            else:
                return stored_hash.verify(password)

            # If the stored password looks like an old-style NAV MD5
            # hash we compute the MD5 hash of the supplied password
            # for comparison.
            if self.password[:3] == 'md5':
                hash = md5.md5(password)
                return (hash.hexdigest() == self.password[3:])
            else:
                return (password == self.password)
        else:
            return False

class AccountGroup(models.Model):
    '''NAV account groups'''

    name = models.CharField()
    description = models.CharField(db_column='descr')
    accounts = models.ManyToManyField('Account') # FIXME this uses a view hack, was AccountInGroup

    class Meta:
        db_table = u'accountgroup'
        ordering = ('name',)

    def __unicode__(self):
        return self.name

class AccountProperty(models.Model):
    '''Key-value for account settings'''

    account = models.ForeignKey('Account', db_column='accountid')
    property = models.CharField()
    value = models.CharField()

    class Meta:
        db_table = u'accountproperty'

    def __unicode__(self):
        return '%s=%s' % (self.property, self.value)

class AccountOrganization(models.Model):
    account = models.ForeignKey('Account', db_column='accountid')
    organization = models.CharField(max_length=30, db_column='orgid')

    class Meta:
        db_table = u'accountorg'

    def __unicode__(self):
        return self.organization

class Privilege(models.Model):
    group = models.ForeignKey('AccountGroup', db_column='accountgroupid')
    type = models.ForeignKey('PrivilegeType', db_column='privilegeid')
    target = models.CharField()

    class Meta:
        db_table = u'accountgroupprivilege'

    def __unicode__(self):
        return self.target


class PrivilegeType(models.Model):
    id = models.AutoField(db_column='privilegeid', primary_key=True)
    name = models.CharField(max_length=30, db_column='privilegename')

    class Meta:
        db_table = u'privilege'

    def __unicode__(self):
        return self.name

class AlertAddress(models.Model):
    '''Accounts alert addresses, valid types are retrived from alertengine.conf'''

    DEBUG_MODE = False

    account = models.ForeignKey('Account', db_column='accountid')
    type = models.IntegerField(choices=DISPATCHER_TYPES)
    address = models.CharField()

    class Meta:
        db_table = u'alertaddress'

    def __unicode__(self):
        return '%s by %s' % (self.address, self.get_type_display())

    # FIXME For some reason 'get_type_display()' does not give the desired
    # result, it returns the first position of the tuple, not the second, which
    # it should. This function returns the second position of the selected
    # type.
    def get_dispatcher_type(self):
        types = dict(DISPATCHER_TYPES)
        return types[unicode(self.type)]

    def send(self, alert, type=_('now'), dispatcher={}):
        '''Handles sending of alerts to with defined alert notification types'''

        # Determine the right language for the user.
        try:
            lang = self.account.accountproperty_set.get(property='language').value or 'en'
        except AccountProperty.DoesNotExist:
            lang = 'en'

        try:
            DISPATCHERS[self.type].send(self, alert, language=lang, type=type)
        except KeyError:
            logger.error('account %s has an unknown alert adress type set, %d, valid types are: %s' % (self.account, self.type, DISPATCHERS))
        except DispatcherException, e:
            logger.critical('%s raised a DispatcherException inidicating that an alert could not be sent: %s' % (DISPATCHERS[self.type], e))
        except Exception, e:
            logger.critical('Unhandeled error from %s: %s' %
                (DISPATCHERS[self.type], ''.join(traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))))


class AlertPreference(models.Model):
    '''AlertProfile account preferences'''

    account = models.OneToOneField('Account', primary_key=True,  db_column='accountid')
    active_profile = models.OneToOneField('AlertProfile', db_column='activeprofile', null=True)
    last_sent_day = models.DateTimeField(db_column='lastsentday')
    last_sent_week = models.DateTimeField(db_column='lastsentweek')

    class Meta:
        db_table = u'alertpreference'

    def __unicode__(self):
        return 'preferences for %s' % self.account


#######################################################################
### Profile models

class AlertProfile(models.Model):
    '''Account AlertProfiles'''

    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7

    VALID_WEEKDAYS = (
        (MONDAY, _('monday')),
        (TUESDAY, _('tuesday')),
        (WEDNESDAY, _('wednesday')),
        (THURSDAY, _('thursday')),
        (FRIDAY, _('friday')),
        (SATURDAY, _('saturday')),
        (SUNDAY, _('sunday')),
    )

    account = models.ForeignKey('Account', db_column='accountid')
    name = models.CharField()
    daily_dispatch_time = models.TimeField(default='08:00')
    weekly_dispatch_day = models.IntegerField(choices=VALID_WEEKDAYS, default=MONDAY)
    weekly_dispatch_time = models.TimeField(default='08:00')

    class Meta:
        db_table = u'alertprofile'

    def __unicode__(self):
        return self.name

    def get_active_timeperiod(self):
        '''Gets the currently active timeperiod for this profile'''
        # Could have been done with a ModelManager, but the logic
        # is somewhat tricky to do with the django ORM.

        now = datetime.now()

        # Limit our query to the correct type of time periods
        if now.isoweekday() in [6,7]:
            valid_during = [TimePeriod.ALL_WEEK,TimePeriod.WEEKENDS]
        else:
            valid_during = [TimePeriod.ALL_WEEK,TimePeriod.WEEKDAYS]

        # The following code should get the currently active timeperiod.
        active_timeperiod = None
        tp = None
        for tp in self.timeperiod_set.filter(valid_during__in=valid_during).order_by('start'):
            if not active_timeperiod or (tp.start <= now.time()):
                active_timeperiod = tp

        # Return the active timeperiod we found or the last one we checked as
        # timeperiods looparound midnight.
        return active_timeperiod or tp

class TimePeriod(models.Model):
    '''Defines TimerPeriods and which part of the week they are valid'''

    ALL_WEEK = 1
    WEEKDAYS = 2
    WEEKENDS = 3

    VALID_DURING_CHOICES = (
        (ALL_WEEK, _('all days')),
        (WEEKDAYS, _('weekdays')),
        (WEEKENDS, _('weekends')),
    )

    profile = models.ForeignKey('AlertProfile', db_column='alert_profile_id')
    start = models.TimeField(db_column='start_time', default='08:00')
    valid_during = models.IntegerField(choices=VALID_DURING_CHOICES, default=ALL_WEEK)

    class Meta:
        db_table = u'timeperiod'

    def __unicode__(self):
        return u'from %s for %s profile on %s' % (self.start, self.profile, self.get_valid_during_display())

class AlertSubscription(models.Model):
    '''Links an address and timeperiod to a filtergroup with a given subscription type'''

    NOW = 0
    DAILY = 1
    WEEKLY = 2
    NEXT = 3

    SUBSCRIPTION_TYPES = (
        (NOW, _('immediately')),
        (DAILY, _('daily at predefined time')),
        (WEEKLY, _('weekly at predefined time')),
        (NEXT, _('at end of timeperiod')),
    )

    alert_address = models.ForeignKey('AlertAddress')
    time_period = models.ForeignKey('TimePeriod')
    filter_group = models.ForeignKey('FilterGroup')
    type = models.IntegerField(db_column='subscription_type', choices=SUBSCRIPTION_TYPES, default=NOW)
    ignore_closed_alerts = models.BooleanField()

    class Meta:
        db_table = u'alertsubscription'

    def __unicode__(self):
        return 'alerts received %s should be sent %s to %s' % (self.time_period, self.get_type_display(), self.alert_address)

    def handle_alert(self, alert):
        '''Decides what to do with an alert based on subscription

           Returns a touple (sent, queued) indicating how many messages have
           been sent and queued'''

        if self.type == self.NOW:
            # Delegate the sending to the alarm address that knows where this
            # message should go.
            self.alert_address.send(alert)

            return (1,0)

        elif self.type in [self.DAILY, self.WEEKLY, self.NEXT]:
            account = self.time_period.profile.account

            obj, created = AccountAlertQueue.objects.get_or_create(account=account, alert=alert, subscription=self)

            if created:
                logger.info('alert %d: added to account alert queue for user %s, should be sent %s' % (alert.id, account, self.get_type_display()))
                return (0,1)
            else:
                logger.info('alert %d: allready in alert queue with same subscription for user %s, should be sent %s' % (alert.id, account, self.get_type_display()))
                return (0,0)

        else:
            logger.error('Alertsubscription %d has an invalid type %d' % (self.id, self.type))

#######################################################################
### Equipment models

class FilterGroupContent(models.Model):
    '''Defines how a given filter should be used in a filtergroup'''

    #            inc   pos
    # Add      |  1  |  1  | union in set theory
    # Sub      |  0  |  1  | exclusion
    # And      |  0  |  0  | intersection in set theory
    # Add inv. |  1  |  0  | complement of set

    # include and positive are used to decide how the match result of the
    # filter should be applied. the table above is an attempt at showing how
    # this should work. Add inv is really the only tricky one, basicly it is
    # nothing more that a negated add, ie if we have a filter  that checks
    # severity > 70 using a add inv on it is equivilent til severity < 70.

    # The actual checking of the FilterGroup is done in the alertengine
    # subsystem in an attempt to keep most of the alerteninge code simple and
    # in one place.

    include = models.BooleanField()
    positive = models.BooleanField()
    priority = models.IntegerField()

    filter = models.ForeignKey('Filter')
    filter_group = models.ForeignKey('FilterGroup')

    class Meta:
        db_table = u'filtergroupcontent'
        ordering = ['priority']

    def __unicode__(self):
        if self.include:
            type = 'inclusive'
        else:
            type = 'exclusive'

        if not self.positive:
            type = 'inverted %s'  % type

        return '%s filter on %s' % (type, self.filter)

class Operator(models.Model):
    '''Defines valid operators for a given matchfield.'''

    EQUALS = 0
    GREATER = 1
    GREATER_EQ = 2
    LESS = 3
    LESS_EQ = 4
    NOT_EQUAL = 5
    STARTSWITH = 6
    ENDSWITH = 7
    CONTAINS = 8
    REGEXP = 9
    WILDCARD = 10
    IN = 11

    # This list designates which operators are supported for any field. The
    # only major special case is IP's which are matched with special pg ip
    # operators where it makes sense, the rest of the operators are handeled
    # with plain text comaparisons against the result of text(ip)
    OPERATOR_TYPES = (
        (EQUALS, _('equals')),
        (GREATER, _('is greater')),
        (GREATER_EQ, _('is greater or equal')),
        (LESS, _('is less')),
        (LESS_EQ, _('is less or equal')),
        (NOT_EQUAL, _('not equals')),
        (STARTSWITH, _('starts with')),
        (ENDSWITH, _('ends with')),
        (CONTAINS, _('contains')),
        (REGEXP, _('regexp')),
        (WILDCARD, _('wildcard (? og *)')),
        (IN, _('in')),
    )

    # This is the mapping that is jused when we try querying the ORM to se if
    # filtes match. Note that wildcard is not here as it neeeds to be special
    # cased.
    OPERATOR_MAPPING = {
        EQUALS: '__exact',
        GREATER: '__gt',
        GREATER_EQ: '__gte',
        LESS: '__lt',
        LESS_EQ: '__lte',
        STARTSWITH: '__istartswith',
        ENDSWITH: '__iendswith',
        CONTAINS: '__icontains',
        REGEXP: '__iregex',
        IN: '__in',
    }

    # The IpAddressField in django does not support ipv6 yet so the IP
    # datatype needs to be completly special cased. The following operator
    # mapping is used to achive this and expects that it will get '% field'
    IP_OPERATOR_MAPPING = {
        EQUALS: '%s = %%s',
        GREATER: '%s > %%s',
        GREATER_EQ: '%s >= %%s',
        LESS: '%s < %%s',
        LESS_EQ: '%s <= %%s',
        NOT_EQUAL: '%s <> %%s',
        CONTAINS: '%s >>= %%s',
        IN: '%s <<= %%s',

        WILDCARD: "host(%s) LIKE %%s",
        REGEXP: "host(%s) ~* %%s",
        STARTSWITH: "host(%s) ILIKE '%%%%' + %%s",
        ENDSWITH: "host(%s) ILIKE %%s + '%%%%'",
    }
    type = models.IntegerField(choices=OPERATOR_TYPES, db_column='operator_id')
    match_field = models.ForeignKey('MatchField')

    class Meta:
        db_table = u'operator'
        unique_together = (('operator', 'match_field'),)

    def __unicode__(self):
        return u'%s match on %s' % (self.get_type_display(), self.match_field)

    def get_operator_mapping(self):
        return self.OPERATOR_MAPPING[self.type]

    def get_ip_operator_mapping(self):
        return self.IP_OPERATOR_MAPPING[self.type]


class Expresion(models.Model):
    '''Combines filer, operator, matchfield and value into an expresion that can be evaluated'''

    filter = models.ForeignKey('Filter')
    match_field = models.ForeignKey('MatchField')
    operator = models.IntegerField(choices=Operator.OPERATOR_TYPES)
    value = models.CharField()

    class Meta:
        db_table = u'expresion'

    def __unicode__(self):
        return '%s match on %s against %s' % (self.get_operator_display(), self.match_field, self.value)

    def get_operator_mapping(self):
        return Operator(type=self.operator).get_operator_mapping()

class Filter(models.Model):
    '''One or more expresions that are combined with an and operation.

    Handles the actual construction of queries to be run taking into account
    special cases like the IP datatype and WILDCARD lookups.'''

    owner = models.ForeignKey('Account')
    name = models.CharField()

    class Meta:
        db_table = u'filter'

    def __unicode__(self):
        return self.name

    def check(self, alert):
        '''Combines expresions to an ORM query that will tell us if an alert matched.

        This function builds three dicts that are used in the ORM .filter()
        .exclude() and .extra() methods which finally gets a .count() as we
        only need to know if something matched.

        Running alertengine in debug mode will print the dicts to the logs.'''

        filter = {}
        exclude = {}
        extra = {'where': [], 'params': []}

        for expresion in self.expresion_set.all():
            # Handle IP datatypes:
            if expresion.match_field.data_type == MatchField.IP:
                # Trick the ORM into joining the tables we want
                lookup = '%s__isnull' % expresion.match_field.get_lookup_mapping()
                filter[lookup] = False

                where = Operator(type=expresion.operator).get_ip_operator_mapping()

                if expresion.operator in [Operator.IN, Operator.CONTAINS]:
                    values = expresion.value.split('|')
                    where = ' OR '.join([where % expresion.match_field.value_id] * len(values))

                    extra['where'].append('(%s)' % where)
                    extra['params'].extend(values)

                else:
                    # Get the IP mapping and put in the field before adding it to
                    # our where clause.
                    extra['where'].append(where % expresion.match_field.value_id)
                    extra['params'].append(expresion.value)

            # Handle wildcard lookups which are not directly supported by
            # django (as far as i know)
            elif expresion.operator == Operator.WILDCARD:
                # Trick the ORM into joining the tables we want
                lookup = '%s__isnull' % expresion.match_field.get_lookup_mapping()
                filter[lookup] = False

                extra['where'].append('%s ILIKE %%s' % expresion.match_field.value_id)
                extra['params'].append(expresion.value)

            # Handle the plain lookups that we can do directly in ORM
            else:
                lookup = expresion.match_field.get_lookup_mapping() + expresion.get_operator_mapping()

                # Ensure that in and not equal are handeled correctly
                if expresion.operator == Operator.IN:
                    filter[lookup] = expresion.value.split('|')
                elif expresion.operator == Operator.NOT_EQUAL:
                    exclude[lookup] = expresion.value
                else:
                    filter[lookup] = expresion.value

        # Limit ourselves to our alert
        filter['id'] = alert.id

        if not extra['where']:
            extra = {}

        logger.debug('alert %d: checking against filter %d with filter: %s, exclude: %s and extra: %s' % (alert.id, self.id, filter, exclude, extra))

        # Check the alert maches whith a SELECT COUNT(*) FROM .... so that the
        # db doesn't have to work as much.
        if AlertQueue.objects.filter(**filter).exclude(**exclude).extra(**extra).count():
            logger.debug('alert %d: matches filter %d' % (alert.id, self.id))
            return True

        logger.debug('alert %d: did not match filter %d' % (alert.id, self.id))
        return False

class FilterGroup(models.Model):
    '''A set of filters group contents that an account can subscribe to or be given permision to'''

    owner = models.ForeignKey('Account')
    name = models.CharField()
    description = models.CharField(db_column='descr')

    group_permisions = models.ManyToManyField('AccountGroup', db_table='filtergroup_group_permision')

    class Meta:
        db_table = u'filtergroup'

    def __unicode__(self):
        return self.name

class MatchField(models.Model):
    '''Defines which fields can be matched upon and how'''

    STRING = 0
    INTEGER = 1
    IP = 2

    # Due to the way alertengine has been reimpleneted the code only really
    # does stuff diffrently if datatype is set to IP, however setting datatype
    # still makes alot of sense in alertprofiles so that we can verify
    # userinput
    DATA_TYPES = (
        (STRING, _('string')),
        (INTEGER, _('integer')),
        (IP, _('ip')),
    )

    # This is a manualy mainted mapping between our model concepts and the
    # actual db tables that are in use. This is needed as our value_id is base
    # on this value.
    ALERT = 'alertq'
    ALERTTYPE = 'alerttype'
    ARP = 'arp'
    CAM = 'cam'
    CATEGORY = 'cat'
    SUBCATEGORY = 'subcat'
    DEVICE = 'device'
    EVENT_TYPE = 'eventtype'
    GWPORT = 'gwport'
    LOCATION = 'location'
    MEMORY = 'mem'
    MODULE = 'module'
    NETBOX = 'netbox'
    NETBOXINFO = 'netboxinfo'
    ORGANIZATION = 'org'
    PREFIX = 'prefix'
    PRODUCT = 'product'
    ROOM = 'room'
    SERVICE = 'service'
    SWPORT = 'swport'
    TYPE = 'type'
    VENDOR = 'vendor'
    VLAN = 'vlan'
    USAGE = 'usage'

    LOOKUP_FIELDS = (
        (ALERT, _('alert')),
        (ALERTTYPE, _('alert type')),
        (ARP, _('arp')),
        (CAM, _('cam')),
        (CATEGORY, _('category')),
        (SUBCATEGORY, _('subcategory')),
        (DEVICE, _('device')),
        (EVENT_TYPE, _('event type')),
        (GWPORT, _('GW-port')),
        (LOCATION, _('location')),
        (MEMORY, _('memeroy')),
        (MODULE, _('module')),
        (NETBOX, _('netbox')),
        (NETBOXINFO, _('netbox info')),
        (ORGANIZATION, _('organization')),
        (PREFIX, _('prefix')),
        (PRODUCT, _('product')),
        (ROOM, _('room')),
        (SERVICE, _('service')),
        (SWPORT, _('SW-port')),
        (TYPE, _('type')),
        (VENDOR, _('vendor')),
        (VLAN, _('vlan')),
        (USAGE, _('usage')),
    )

    # This mapping designates how a MatchField relates to an alert. (yes the
    # formating is not PEP8, but it wouldn't be very readable otherwise)
    # Since we need to know how things are connected this has been done manualy
    FOREIGN_MAP = {
        ARP:          'netbox__arp',
        CAM:          'netbox__cam',
        CATEGORY:     'netbox__category',
        SUBCATEGORY:  'netbox__category__subcategory',
        DEVICE:       'netbox__device',
        EVENT_TYPE:   'event_type',
        GWPORT:       'netbox__connected_to_gwport',
        LOCATION:     'netbox__room__location',
        MEMORY:       'netbox__memory',
        MODULE:       'netbox__module',
        NETBOX:       'netbox',
        NETBOXINFO:   'netbox__info',
        ORGANIZATION: 'netbox__organization',
        PREFIX:       'netbox__prefix',
        PRODUCT:      'netbox__device__product',
        ROOM:         'netbox__room',
        SERVICE:      'netbox__service',
        SWPORT:       'netbox__connected_to_swport',
        TYPE:         'netbox__type',
        USAGE:        'netbox__organization__vlan__usage',
        VENDOR:       'netbox__device__product__vendor',
        VLAN:         'netbox__organization__vlan',
        ALERT:        '', # Checks alert object itself
        ALERTTYPE:    'alert_type',
    }

    # Build the mapping we need to be able to do checks.
    VALUE_MAP = {}
    CHOICES = []
    MODEL_MAP = {}

    # This code loops over all the SUPPORTED_MODELS and gets the db_table and
    # db_column so that we can translate them into the correspinding attributes
    # on our django models. (field and model need to be set to None to avoid an
    # ugly side effect of field becoming an acctuall field on MatchField)
    for model in SUPPORTED_MODELS:
        for field in model._meta.fields:
            key = '%s.%s' % (model._meta.db_table, field.db_column or field.attname)
            value = '%s__%s' % (FOREIGN_MAP[model._meta.db_table], field.attname)

            VALUE_MAP[key] = field.attname
            CHOICES.append((key, value.lstrip('_')))
            MODEL_MAP[key] = (model, field.attname)
        field = None
    model = None

    name = models.CharField()
    description = models.CharField(db_column='descr', blank=True)
    value_help = models.CharField(u'Help text for the matchfield', blank=True, help_text=u'Displayed by the value input box in the GUI to help users enter sane values.')
    value_id = models.CharField(u'Matchfield, the database field to watch', choices=CHOICES, help_text=u'This is the acctual field alert engine will watch.')
    value_name = models.CharField(u'Description for the matchfield used in the GUI', choices=CHOICES, blank=True, help_text=u'Only used in the GUI to show additonal description of the matchfield. Only does something when "Show list" is checked.')
    value_sort = models.CharField(u'Order matchfields by this field', choices=CHOICES, blank=True, help_text=u'Options in the list will be ordered by this field (if not set, options will be ordered by primary key). Only does something when "Show list" is checked.')
    list_limit = models.IntegerField(blank=True, help_text=u'Only this many options will be available in the list. Only does something when "Show list" is checked.')
    data_type = models.IntegerField(choices=DATA_TYPES, help_text=u'The data type of the match field. Purely cosmetic')
    show_list = models.BooleanField(blank=True, help_text=u'If unchecked values can be entered into a text input. If checked values must be selected from a list populated by data from the match field selected above.')

    class Meta:
        db_table = u'matchfield'

    def __unicode__(self):
        return self.name

    def get_lookup_mapping(self):
        try:
            foreign_lookup = self.FOREIGN_MAP[self.value_id.split('.')[0]]
            value = self.VALUE_MAP[self.value_id]

            if foreign_lookup:
                return '%s__%s' % (foreign_lookup, value)
            return value

        except KeyError:
            logger.error("Tried to lookup mapping for %s which is not supported" % self.value_id)
        return None


#######################################################################
### AlertEngine models

class SMSQueue(models.Model):
    '''Queue of messages that should be sent or have been sent by SMSd'''

    SENT = 'Y'
    NOT_SENT = 'N'
    IGNORED = 'I'

    SENT_CHOICES = (
        (SENT, _('sent')),
        (NOT_SENT, _('not sent yet')),
        (IGNORED, _('ignored')),
    )

    id = models.IntegerField(primary_key=True)
    account = models.ForeignKey('Account', db_column='accountid')
    time = models.DateTimeField(auto_now_add=True)
    phone = models.CharField(max_length=15)
    message = models.CharField(max_length=145, db_column='msg')
    sent = models.CharField(max_length=1, default=NOT_SENT, choices=SENT_CHOICES)
    sms_id = models.IntegerField(db_column='smsid')
    time_sent = models.DateTimeField(db_column='timesent')
    severity = models.IntegerField()

    class Meta:
        db_table = u'smsq'

    def __unicode__(self):
        return '"%s" to %s, sent: %s' % (self.message, self.phone, self.sent)

    def save(self, *args, **kwargs):
        # Truncate long messages (max is 145)
        if len(self.message) > 142:
            self.message = self.message[:142] + '...'

        return super(SMSQueue, self).save(*args, **kwargs)

class AccountAlertQueue(models.Model):
    '''Defines which alerts should be keept around and sent at a later time'''

    account = models.ForeignKey('Account')
    subscription = models.ForeignKey('AlertSubscription')
    alert = models.ForeignKey('AlertQueue')
    insertion_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = u'accountalertqueue'

    def delete(self, *args, **kwargs):
        # TODO deleting items with the manager will not trigger this behaviour
        # cleaning up related messages.

        super(AccountAlertQueue, self).delete(*args, **kwargs)

        # Remove the alert from the AlertQueue if we are the last item
        # depending upon it.
        if self.alert.accountalertqueue_set.count() == 0:
            self.alert.delete()

    def send(self):
        '''Sends the alert in question to the address in the subscription'''
        self.subscription.alert_address.send(self.alert, type=self.subscription.get_type_display())

        self.delete()
