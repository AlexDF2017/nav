#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2006 UNINETT AS
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

"""
The smsd queue for the NAV database.

This smsd queue takes care of all communication between smsd and the NAV
database. Replacing the NAV database with some other queue/input should be
possible by implementing the interface seen in this class.

Generally, a phone number is a user and vice versa.
"""

__copyright__ = "Copyright 2006 UNINETT AS"
__license__ = "GPL"
__author__ = "Stein Magnus Jodal (stein.magnus@jodal.no)"
__id__ = "$Id$"

import logging
import nav.db
import sys

class NAVDBQueue(object):
    "The smsd queue for the NAV database."
    def __init__(self):
        """Constructor."""

        # Create logger
        self.logger = logging.getLogger("nav.smsd.queue")

        # Open DB connection early so we can detect errors early
        try:
            dbconn = nav.db.getConnection('smsd', 'navprofile')
        except Exception, error:
            self.logger.exception("Queue failed to initialize. Exiting. (%s)",
             error)
            sys.exit(1)

    def cancel(self, minage = '0'):
        """
        Mark all unsent messages as ignored.

        Input:
            minage  Minimum age required for canceling message, default '0'.
                    Format as PostgreSQL interval type, e.g. '1 day 12 hours'.
        
        Returns number of messages canceled.
        """

        dbconn = nav.db.getConnection('smsd', 'navprofile')
        db = dbconn.cursor()

        data = { 'minage': str(minage) }

        # Test minage
        if minage != '0':
            sql = "SELECT interval %(minage)s"
            try:
                db.execute(sql, data)
            except nav.db.driver.ProgrammingError, error:
                self.logger.warning("'autocancel' value (%s) is not valid. " +
                                    "Check config for errors.",
                                    minage)
                return 0
            except Exception, error:
                self.logger.error("Unknown exception caught in cancel(). " +
                                  "Exiting.")
                sys.exit(1)

        # Ignore messages
        sql = """UPDATE smsq SET sent = 'I'
            WHERE sent = 'N' AND time < now() - interval %(minage)s"""
        db.execute(sql, data)
        dbconn.commit()

        return db.rowcount

    def getusers(self, sent = 'N'):
        """
        Get users which has messages with given sent status (normally unsent).
        
        Returns a sorted list with the phone numbers for all users with
        messages with given sent status.
        """
        
        users = []
        dbconn = nav.db.getConnection('smsd', 'navprofile')
        db = dbconn.cursor()

        sql = "SELECT DISTINCT phone FROM smsq " + \
            "WHERE sent = '%s' " % sent + \
            "ORDER BY phone"
        db.execute(sql)
        result = db.fetchall()
        # Rollback so we don't have old open transactions which foobars the
        # usage of now() in setsentstatus()
        dbconn.rollback()

        # Create a simple list without the tuples
        for row in result:
            users.append(row[0])

        return users

    def getusermsgs(self, user, sent = 'N'):
        """
        Get the users messages which has given sent status (normally unsent).
        
        Returns a list of messsages ordered with the most severe first. Each
        message is a tuple with the ID, text, and severity of the message.
        """

        messages = []
        dbconn = nav.db.getConnection('smsd', 'navprofile')
        db = dbconn.cursor()

        sql = "SELECT id, msg, severity FROM smsq " + \
            "WHERE phone = '%s' AND sent = '%s' " % (user, sent) + \
            "ORDER BY severity DESC, time ASC"
        db.execute(sql)
        result = db.fetchall()
        # Rollback so we don't have old open transactions which foobars the
        # usage of now() in setsentstatus()
        dbconn.rollback()

        return result

    def setsentstatus(self, id, sent, smsid = 0):
        """
        Set the sent status of a message given ID and status.

        Returns number of messages changed.
        """

        dbconn = nav.db.getConnection('smsd', 'navprofile')
        db = dbconn.cursor()

        timesent = ''
        if sent == 'Y' or sent == 'I':
            timesent = ', timesent = now()'

        sql = "UPDATE smsq SET sent = '%s', smsid = '%d'%s WHERE id = '%d'" \
         % (sent, smsid, timesent, id)

        db.execute(sql)
        dbconn.commit()

        return db.rowcount
