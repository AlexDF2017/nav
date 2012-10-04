#
# Copyright (C) 2010 UNINETT AS
#
# This file is part of Network Administration Visualized (NAV).
#
# NAV is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.  You should have received a copy of the GNU General Public License
# along with NAV. If not, see <http://www.gnu.org/licenses/>.
#
"""A high level interface to SNMP query functionality for NAV, as pysnmp is
quite low-level and tedious to work with.

This interface supports both PySNMP v2 and PySNMP SE.
"""
# Debian enables multi-version installs of pysnmp.  On Debian, settings this
# environment variable will select PySNMP-SE, which is the highest version
# supported by NAV.
import os
os.environ['PYSNMP_API_VERSION'] = 'v3'

try:
    import pysnmp
except ImportError, e:
    os.environ['PYSNMP_API_VERSION'] = 'v2'
    import pysnmp

# Identify which PySNMP version is actually installed.  Looks ugly, but each
# version provides (or forgets to provide) a different API for reporting its
# version.
backend = None
try:
    from pysnmp import version
    version.verifyVersionRequirement(3, 4, 3)
    backend = 'se'
except ImportError, e:
    if hasattr(pysnmp, 'majorVersionId'):
        raise ImportError('Unsupported PySNMP version ' %
                          pysnmp.majorVersionId)
    else:
        backend = 'v2'

if backend == 'v2':
    from pysnmp_v2 import *
elif backend == 'se':
    from pysnmp_se import *
else:
    raise ImportError("Unsupported PySNMP version installed")
