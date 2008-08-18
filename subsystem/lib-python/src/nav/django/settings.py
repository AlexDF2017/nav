# -*- coding: utf-8 -*-
#
# Copyright 2007,2008 UNINETT AS
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

"""Django configuration wrapper around the NAV configuration files"""

__copyright__ = "Copyright 2007,2008 UNINETT AS"
__license__ = "GPL"
__author__ = "Stein Magnus Jodal (stein.magnus.jodal@uninett.no)"
__id__ = "$Id$"

from nav.config import readConfig
import nav.buildconf
import nav.path

if 'DJANGO_DEBUG' in readConfig('nav.conf') \
    and readConfig('nav.conf')['DJANGO_DEBUG'] == "True":
    DEBUG = True
else:
    DEBUG = False
TEMPLATE_DEBUG = DEBUG

# Admins
ADMINS = (
    ('NAV Administrator', readConfig('nav.conf')['ADMIN_MAIL']),
)
MANAGERS = ADMINS

# Database / ORM configuration
db_config = readConfig('db.conf')
DATABASE_ENGINE = 'postgresql_psycopg2'
DATABASE_NAME = db_config['db_nav']
DATABASE_USER = db_config['script_django']
DATABASE_PASSWORD = db_config['userpw_%s' % DATABASE_USER]
DATABASE_HOST = db_config['dbhost']
DATABASE_PORT = db_config['dbport']

# URLs configuration
ROOT_URLCONF = 'nav.django.urls'

# Templates
TEMPLATE_DIRS = (
    nav.path.djangotmpldir,
)
TEMPLATE_CONTEXT_PROCESSORS = (
    'nav.django.context_processors.debug',
)

# Date formatting
DATE_FORMAT = 'Y-m-d'
TIME_FORMAT = 'H:i:s'
DATETIME_FORMAT = '%s %s' % (DATE_FORMAT, TIME_FORMAT)

TIME_ZONE = 'Europe/Oslo'
