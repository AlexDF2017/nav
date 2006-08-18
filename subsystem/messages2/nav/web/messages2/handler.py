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
#
# Author: Stein Magnus Jodal <stein.magnus@jodal.no>
#

"""
mod_python handler for the Message2 subsystem.
"""

__copyright__ = "Copyright 2006 UNINETT AS"
__license__ = "GPL"
__author__ = "Stein Magnus Jodal (stein.magnus@jodal.no)"
__id__ = "$Id:$"

import time
from mod_python import apache, util
import mx.DateTime

import nav.db
from nav.web.URI import URI
from nav.web.templates.Messages2ListTemplate import Messages2ListTemplate
from nav.web.templates.Messages2NewTemplate import Messages2NewTemplate
from nav.web.templates.Messages2FeedTemplate import Messages2FeedTemplate
from nav.web.messages2 import messages2
from nav.web.maintenance2 import maintenance2

dbconn = nav.db.getConnection('webfront', 'manage')
db = dbconn.cursor()

def handler(req):
    """Handler for the Messages 2 subsystem."""

    # Initialize form
    keep_blank_values = True
    req.form = util.FieldStorage(req, keep_blank_values)

    # Get arguments
    args = URI(req.unparsed_uri)

    # Get section
    if len(args.path.split('/')[-1]):
        section = args.path.split('/')[-1]
    else:
        section = 'active'
 
    ### SECTIONS
    # RSS 2.0 feed
    if section == 'rss':
        page = Messages2FeedTemplate()
        page.msgs = messages2.getMsgs('publish_start < now() AND publish_end > now() AND replaced_by IS NULL')

        page.channeltitle = 'NAV Message Feed from ' + req.hostname
        page.channeldesc = page.channeltitle
        page.channellink = 'http://' + req.hostname + args.path
        page.channellang = 'en-us'
        page.channelttl = '60'

        page.pubDate = 0
        for i, msg in enumerate(page.msgs):
            if msg['publish_start'] > page.pubDate:
                page.pubDate = msg['publish_start']
            page.msgs[i]['link'] = 'http://' + req.hostname \
                + '/messages2/view?id=' + str(page.msgs[i]['messageid'])
            page.msgs[i]['guid'] = page.msgs[i]['link']
        if page.pubDate == 0:
            page.pubDate = mx.DateTime.now()

        # Done, output the page
        req.content_type = 'text/xml'
        req.send_http_header()
        req.write(page.respond())
        return apache.OK
    # Planned messages (not yet reached publishing time)
    elif section == 'planned':
        page = Messages2ListTemplate()
        page.title = 'Planned Messages'
        page.msgs = messages2.getMsgs('publish_start > now() AND publish_end > now() AND replaced_by IS NULL')

    # Historic and replaced messages
    elif section == 'historic':
        page = Messages2ListTemplate()
        page.title = 'Historic Messages'
        page.msgs = messages2.getMsgs('publish_end < now() OR replaced_by IS NOT NULL', 'publish_end DESC')

    # View a message
    elif section == 'view' and args.get('id').isdigit():
        page = Messages2ListTemplate()
        page.title = 'Message'
        msgid = int(args.get('id'))
        page.msgs = messages2.getMsgs('messageid = %d' % msgid)

    # Expire a message
    elif section == 'expire' and args.get('id').isdigit():
        page = Messages2ListTemplate()
        page.title = 'Expire message'
        page.infomsgs = []
        msgid = int(args.get('id'))
        messages2.expireMsg(msgid)
        page.infomsgs.append('The following message was expired.')
        page.msgs = messages2.getMsgs('messageid = %d' % msgid)

    # New, followup and edit message
    elif section == 'new' or section == 'edit' or section == 'followup':
        page = Messages2NewTemplate()
        page.title = 'Create New Message'
        page.tasks = maintenance2.getTasks('maint_end > now()')
        page.errors = []

        # Followup
        if section == 'followup':
            page.current = 'new' # Just to mark the menu tab
            if not args.get('id').isdigit():
                page.errors.append('Message ID in request is not a digit.')
            else:
                msgid = int(args.get('id'))
                page.replaces_messageid = msgid
                page.replaces_message = messages2.getMsgs('messageid = %d' \
                    % msgid)[0]

        # Edit
        if section == 'edit':
            page.title = 'Edit Message'
            page.submittext = 'Save Message'
            if not args.get('id').isdigit():
                page.errors.append('Message ID in request is not a digit.')
            else:
                msgid = int(args.get('id'))
                msg = messages2.getMsgs('messageid = %d' % msgid)[0]

                page.edit_messageid = msgid
                page.formtitle = msg['title']
                page.description = msg['description']
                page.tech_description = msg['tech_description']

                page.start_year = int(msg['publish_start'].strftime('%Y'))
                page.start_month = int(msg['publish_start'].strftime('%m'))
                page.start_day = int(msg['publish_start'].strftime('%d'))
                page.start_hour = int(msg['publish_start'].strftime('%H'))
                page.start_min = int(msg['publish_start'].strftime('%M'))

                page.end_year = int(msg['publish_end'].strftime('%Y'))
                page.end_month = int(msg['publish_end'].strftime('%m'))
                page.end_day = int(msg['publish_end'].strftime('%d'))
                page.end_hour = int(msg['publish_end'].strftime('%H'))
                page.end_min = int(msg['publish_end'].strftime('%M'))

                if type(msg['replaces_message']) is int:
                    page.replaces_messageid = msg['replaces_message']
                    page.replaces_message = messages2.getMsgs('messageid = %d' \
                        % page.replaces_messageid)[0]
                else:
                    page.replaces_messageid = False

                if type(msg['tasks']) is list:
                    page.maint_tasks = []
                    for task in msg['tasks']:
                        page.maint_tasks.append(str(task['maint_taskid']))
                else:
                    page.maint_tasks = []

        # Form submitted
        page.submit = req.form.has_key('submit')
        if page.submit:
            # Get and control form data
            if req.form.has_key('title') and req.form['title']:
                title = req.form['title']
                page.formtitle = title
            else:
                page.errors.append('You did not supply a title.')

            # Descriptions
            if req.form.has_key('description') and req.form['description']:
                description = req.form['description']
                page.description = description
            else:
                page.errors.append('You did not supply a description.')

            if req.form.has_key('tech_description') and len(req.form['tech_description']) > 0:
                tech_description = req.form['tech_description']
                page.tech_description = tech_description
            else:
                tech_description = False

            # Publish times
            if (req.form.has_key('start_year') and req.form['start_year']
                and req.form.has_key('start_month') and req.form['start_month']
                and req.form.has_key('start_day') and req.form['start_day']
                and req.form.has_key('start_hour') and req.form['start_hour']
                and req.form.has_key('start_min') and req.form['start_min']):
                publish_start = '%4d-%02d-%02d %02d:%02d' % (
                    int(req.form['start_year']), int(req.form['start_month']),
                    int(req.form['start_day']), int(req.form['start_hour']),
                    int(req.form['start_min']))
                publish_start = time.strptime(publish_start, '%Y-%m-%d %H:%M')

                page.start_year = int(req.form['start_year'])
                page.start_month = int(req.form['start_month'])
                page.start_day = int(req.form['start_day'])
                page.start_hour = int(req.form['start_hour'])
                page.start_min = int(req.form['start_min'])
            else:
                publish_start = time.localtime()
            
            if (req.form.has_key('end_year') and req.form['end_year']
                and req.form.has_key('end_month') and req.form['end_month']
                and req.form.has_key('end_day') and req.form['end_day']
                and req.form.has_key('end_hour') and req.form['end_hour']
                and req.form.has_key('end_min') and req.form['end_min']):
                publish_end = '%4d-%02d-%02d %02d:%02d' % (
                    int(req.form['end_year']), int(req.form['end_month']),
                    int(req.form['end_day']), int(req.form['end_hour']),
                    int(req.form['end_min']))
                publish_end = time.strptime(publish_end, '%Y-%m-%d %H:%M')

                page.end_year = int(req.form['end_year'])
                page.end_month = int(req.form['end_month'])
                page.end_day = int(req.form['end_day'])
                page.end_hour = int(req.form['end_hour'])
                page.end_min = int(req.form['end_min'])
            else:
                publish_end = time.localtime(int(time.time()) + 7*24*60*60)

            if publish_start > publish_end:
                page.errors.append('Publish end is before start, ' \
                    + 'message will never be published.')
            
            # Maintenance tasks
            if req.form.has_key('maint_tasks'):
                maint_tasks = req.form['maint_tasks']
                if type(maint_tasks) is not list:
                    maint_tasks = [maint_tasks]
                try:
                    maint_tasks.remove('none')
                except ValueError, error:
                    pass
                page.maint_tasks = maint_tasks
            else:
                maint_tasks = []

            # Followup
            if req.form.has_key('replaces_messageid') \
                and req.form['replaces_messageid']:
                replaces_messageid = int(req.form['replaces_messageid'])
                page.replaces_messageid = replaces_messageid
            else:
                replaces_messageid = False

            # Get ID of message edited
            if section == 'edit':
                if req.form.has_key('edit_messageid') \
                    and req.form['edit_messageid']:
                    edit_messageid = int(req.form['edit_messageid'])
                else:
                    page.errors.append('ID of edited message is missing.')

            # Get session data
            author = req.session['user'].login

            # If any data not okay, form is showed with list of errors on top.
            # There is no need to do anything further here.
            if len(page.errors):
                pass
            # No errors, update database
            else:
                if section == 'edit':
                    msgid = edit_messageid
                else:
                    msgid = False

                # Update/Insert message
                msgid = messages2.setMsg(msgid, title, description,
                    tech_description, publish_start, publish_end, author,
                    replaces_messageid)

                # For updates, remove all existing task connections
                if section == 'edit':
                    messages2.removeMsgTasks(msgid)

                # Connect with task
                for taskid in maint_tasks:
                    messages2.setMsgTask(msgid, int(taskid))

                # Expire replaced messages
                # If a msg is "unreplaced" it will still be expired
                #if replaces_messageid:
                #    messages2.expireMsg(replaces_messageid)

                # Redirect to view?id=$newid and exit
                req.headers_out['location'] = 'view?id=' + str(msgid)
                req.status = apache.HTTP_MOVED_TEMPORARILY
                req.send_http_header()
                return apache.OK

    # Default: Show active messages (public messages)
    else:
        page = Messages2ListTemplate()
        page.title = 'Active Messages'
        page.msgs = messages2.getMsgs('publish_start < now() AND publish_end > now() AND replaced_by IS NULL')

    # Check if user is logged in
    if req.session['user'].id != 0:
        page.authorized = True
    else:
        page.authorized = False

    # Create menu
    page.menu = []
    page.menu.append({'link': 'active', 'text': 'Active', 'admin': False})
    page.menu.append({'link': 'planned', 'text': 'Planned', 'admin': False})
    page.menu.append({'link': 'historic', 'text': 'Historic', 'admin': False})
    if page.authorized:
        page.menu.append({'link': 'new', 'text': 'Create new', 'admin': True})

    if not page.hasVar('current'):
        page.current = section
    if not page.hasVar('submittext'):
        page.submittext = page.title

    # Done, output the page
    req.content_type = 'text/html'
    req.send_http_header()
    req.write(page.respond())
    return apache.OK
