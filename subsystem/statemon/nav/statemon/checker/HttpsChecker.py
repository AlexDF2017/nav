# -*- coding: ISO8859-1 -*-
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
# $Id: $
# Authors: Magnus Nordseth <magnun@itea.ntnu.no>
#

import httplib
import socket
from urlparse import urlsplit
from nav.statemon.event import Event
from nav.statemon.abstractChecker import AbstractChecker
from nav.statemon import Socket

class HTTPConnection(httplib.HTTPConnection):
	def __init__(self,timeout,host,port=80):
		httplib.HTTPConnection.__init__(self,host,port)
		self.timeout = timeout
		self.connect()
	def connect(self):
		self.sock = Socket.Socket(self.timeout)
		self.sock.connect((self.host,self.port))
class HTTPSConnection(httplib.HTTPSConnection):
	def __init__(self,timeout,host,port=443):
		httplib.HTTPSConnection.__init__(self,host,port)
		self.timeout = timeout
		self.connect()
	def connect(self):
		sock = Socket.Socket(self.timeout)
		sock.connect((self.host,self.port))
		ssl = socket.ssl(sock.s, None, None)
		self.sock = httplib.FakeSocket(sock, ssl)
		
class HttpsChecker(AbstractChecker):
	def __init__(self,service, **kwargs):
		AbstractChecker.__init__(self, "https", service, port=0, **kwargs)
	def execute(self):
		ip, port = self.getAddress()
		args = self.getArgs()
		url = args.get('url','')
		username = args.get('username')
		password = args.get('password','')
		if not url:
			url = "/"
		protocol, vhost, path, query, fragment = urlsplit(url)
		
		i = HTTPSConnection(self.getTimeout(), ip, port or 443)

		if vhost:
			i.host=vhost
		
		i.putrequest('GET',path)
		internalRev = "$Rev: 1361 $"
		internalRev = internalRev[:-2].replace('$Rev: ','')
		i.putheader('User-Agent','NAV/ServiceMon Build 1734 Release 31337, internal revision %s' % internalRev)
		if username:
			auth="%s:%s" % (username, password)
			i.putheader("Authorization", "Basic %s" % auth.encode("base64"))
		i.endheaders()
		response = i.getresponse()
		if response.status >= 200 and response.status < 400:
			status = Event.UP
			version = response.getheader('SERVER')
			self.setVersion(version)
			info= 'OK (%s) %s' % (str(response.status), version)
		else:
			status = Event.DOWN
			info = 'ERROR (%s) %s'  % (str(response.status),url)

		return status,info


def getRequiredArgs():
	"""
	Returns a list of required arguments
	"""
	requiredArgs = []
	return requiredArgs
								
