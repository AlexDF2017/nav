#
# Copyright (C) 2014 UNINETT AS
#
# This file is part of Network Administration Visualized (NAV).
#
# NAV is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.  You should have received a copy of the GNU General Public
# License along with NAV. If not, see <http://www.gnu.org/licenses/>.
#
"""Controllers for the getting started widget"""

from . import Navlet


class GettingStartedWidget(Navlet):
    """Getting Started widget"""

    title = 'Getting started with NAV'
    description = 'Displays a tour and information for new users'
    can_be_added = False

    def get_template_basename(self):
        return 'getting_started'


