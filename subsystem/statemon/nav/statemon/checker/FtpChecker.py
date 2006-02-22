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
# $Id$
# Authors: Magnus Nordseth <magnun@itea.ntnu.no>
#

from nav.statemon.abstractChecker import AbstractChecker
from nav.statemon.event import Event
from nav.statemon import Socket
import ftplib

class FTP(ftplib.FTP):
	def __init__(self,timeout,host='',user='',passwd='',acct=''):
		ftplib.FTP.__init__(self)
		if host:
			self.connect(host)
		if user:
			self.login(user,passwd,acct)
		self.timeout = timeout
	def connect(self, host = '', port = 0):
		'''Connect to host.  Arguments are:
		- host: hostname to connect to (string, default previous host)
		- port: port to connect to (integer, default previous port)'''
		if host: self.host = host
		if port: self.port = port
		msg = "getaddrinfo returns an empty list"
		self.sock = Socket.Socket(self.timeout)
		self.sock.connect((self.host, self.port))
		self.file = self.sock.makefile('rb')
		self.welcome = self.getresp()
		return self.welcome

class FtpChecker(AbstractChecker):
	"""
	takes the args:
	username
	password
	path (ACCT)
	"""
	def __init__(self,service, **kwargs):
		AbstractChecker.__init__(self, "ftp", service, port=0, **kwargs)

	def execute(self):
		s = FTP(self.getTimeout())
		ip, port = self.getAddress()
		output = s.connect(ip,port or 21)
		args = self.getArgs()
		username = args.get('username','')
		password = args.get('password','')
		path = args.get('path','')
		output = s.login(username,password,path)
		print output
		if output[:3] == '230':
			return Event.UP,'code 230'
		else:
			return Event.DOWN,output.split('\n')[0]

def getRequiredArgs():
	"""
	Returns a list of required arguments
	"""
	requiredArgs = []
	return requiredArgs
			
