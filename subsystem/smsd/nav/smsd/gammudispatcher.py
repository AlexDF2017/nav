#! /usr/bin/env python
# -*- coding: ISO8859-1 -*-
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
The smsd dispatcher for Gammu.

This dispatcher takes care of all communication between smsd and Gammu. Gammu
is used to send SMS messages via a cell phone connected to the server with a
serial cable, USB cable, IR or Bluetooth. See http://www.gammu.org/ for more
information.

Depends on python-gammu.
"""

__copyright__ = "Copyright 2006 UNINETT AS"
__license__ = "GPL"
__author__ = "Stein Magnus Jodal (stein.magnus@jodal.no)"
__id__ = "$Id$"

from nav.smsd.dispatcher import *

try:
    import gammu
except ImportError, error:
    raise DispatcherError, 'python-gammu not installed or misconfigured.'

class GammuDispatcher(Dispatcher):
    """The smsd dispatcher for Gammu."""

    def __init__(self, config):
        """Constructor."""

        # Call mother's init
        Dispatcher.__init__(self)

    def sendsms(self, phone, msgs):
        """
        Send SMS using Gammu.

        Arguments:
            ``phone'' is the phone number the messages are to be dispatched to.
            ``msgs'' is a list of messages ordered with the most severe first.
            Each message is a tuple with ID, text and severity of the message.

        Returns five values:
            The formatted SMS.
            A list of IDs of sent messages.
            A list of IDs of ignored messages.
            A boolean which is true for success and false for failure.
            An integer which is the sending ID if available or 0 otherwise.
        """

        # Format SMS
        (sms, sent, ignored) = self.formatsms(msgs)

        # We got a python-gammu binding :-)
        sm = gammu.StateMachine()

        try:
            # Typically ~root/.gammurc or ~navcron/.gammurc
            sm.ReadConfig()
        except IOError, error:
            raise DispatcherError, error

        try:
            # Fails if e.g. phone is not connected
            # See http://www.gammu.org/wiki/index.php?title=Gammu:Error_Codes
            # for complete list of errors fetched here
            sm.Init()
        except gammu.GSMError, error:
            raise DispatcherError, \
             "GSM error %d: %s" % (error[0]['Code'], error[0]['Text'])

        # Tested with Nokia 6610, Tekram IRmate 410U and Gammu 1.07.00
        message = {'Text': sms, 'SMSC': {'Location': 1}, 'Number': phone}
        smsid = sm.SendSMS(message)

        if smsid:
            result = True
        else:
            result = False

        return (sms, sent, ignored, result, smsid)

