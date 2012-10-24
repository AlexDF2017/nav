# -*- coding: UTF-8 -*-
#
# Copyright (C) 2011 UNINETT AS
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
"""macwatch view definitions"""

import logging
import os
import datetime
from ConfigParser import ConfigParser

from django.http import HttpResponseRedirect, HttpResponseForbidden, \
    HttpResponse
from django.template import RequestContext
#from django.template import Context
from django.shortcuts import render_to_response

import nav

from nav.django.utils import get_account

from nav.models.logger import LogMessage
from nav.models.logger import ErrorError
from nav.models.logger import MessageView

from nav.web.loggerhandler.utils import DbAccess
from nav.web.loggerhandler.utils import ParamUtil


NAVBAR = [('Home', '/'), ('Syslog Analyzer', None)]
DEFAULT_VALUES = {'title': "Syslog Analyzer", 'navpath': NAVBAR}

DATEFORMAT = "%Y-%m-%d %H:%M:%S"

logger = logging.getLogger("nav.web.loggerhandler")


def _get_basic_info_dict(db_access, param_util):
    """
    Get all default parameters for view.
    """
    links = []
    error_list = []
    tfrom = param_util.get_time_from()
    if tfrom:
        links.append('tfrom=%s' % tfrom.strftime(DATEFORMAT))
    else:
        error_list.append('Illegal from date (YYYY-MM-DD hh:mm:ss).')
    tto = param_util.get_time_to()
    if tto:
        links.append('tto=%s' % tto.strftime(DATEFORMAT))
    else:
        error_list.append('Illegal to date (YYYY-MM-DD hh:mm:ss).')
    priority =  param_util.get_priority()
    if priority:
        links.append('priority=%d' % priority)
    type_param = param_util.get_type()
    if type_param:
        links.append('type=%d' % type_param)
    origin = param_util.get_origin()
    if origin:
        links.append('origin=%d' % origin)
    category = param_util.get_category()
    if category:
        links.append('category=%d' % category)

    link = "&amp;".join(links)

    info_dict = {'priority': param_util.get_priority(),
                 'origin': origin_param,
                 'originid': db_access.get_origin2originid().get(origin_param,
                                                                None),
                 'category': param_util.get_category(),
                 'type': type_param,
                 'typeid': db_access.get_type2typeid().get(type_param, None),
                 'tto': param_util.get_time_to(),
                 'tfrom': param_util.get_time_from(),
                 'priorities': db_access.get_priorities(),
                 'types': db_access.get_types(),
                 'categories': db_access.get_categories(),
                 'origins': db_access.get_origins(),
                 'origindict':  db_access.get_originid2origin(),
                 'typedict': db_access.get_typeid2type(),
                 'link': link,
                 'error_list': error_list,
                 }
    log = param_util.get_log()
    if log:
        info_dict['log'] = log
    info_dict.update(DEFAULT_VALUES)
    return info_dict


def index(request):
    """
    Default handler.
    """
    account = get_account(request)
    if not account:
        return HttpResponseForbidden("You must be logged in to access this resource")

    tfrom_param = request.GET.get('tfrom', None)
    tto_param = request.GET.get('tto', None)
    priority_param = request.GET.get('priority', None)
    type_param = request.GET.get('type', None)
    origin_param = request.GET.get('origin', None)
    category_param = request.GET.get('category', None)
    log_param = request.GET.get('log', None)

    # convert to datetime or set current timestamp if not requested any format
    if not tto_param:
        tto_param = datetime.datetime.now()
    else:
        tto_param = datetime.time.striptime(tto_param, DATEFORMAT)
    # todo: make sure tfrom is 1 hour before tto_param.
    if not tfrom_param:
        tfrom_param = datetime.datetime.now()
    else:
        tfrom_param = datetime.time.striptime(tfrom_param, DATEFORMAT)


    if ((origin_param and type_param) or (origin_param and log_param)
            or (type_param and log_param)):
        # todo: no such method as log_response(request, db_access, param_util) from patch
        return HttpResponse("No idea what it should respond with yet, dummy data")
    elif origin_param or type_param or priority_param:
        return statistics_reponse(request)

    # priotities-mode
    query = None
    if type_param:
        query = MessageView.objects.filter(type=type_param)
    if origin_param:
        if not query:
            query = MessageView.objects.filter(origin=origin_param)
        else:
            query = query.filter(origin=origin_param)
    if priority_param:
        if not query:
            query = MessageView.objects.filter(newpriority=priority_param)
        else:
            query = query.filter(newpriority=priority_param)
    if category_param:
        if not query:
            query = MessageView.objects.filter(category=category_param)
        else:
            query = query.filter(category=category_param)
    if tfrom_param:
        if not query:
            query =  MessageView.objects.filter(time__gte=tfrom_param)
        else:
            query = query.filter(time__gte=tfrom_param)
    if tto_param:
        if not query:
            query =  MessageView.objects.filter(time__lte=tto_param)
        else:
            query = query.filter(time__lte=tto_param)
    #if not query:
    #    query = MessageView.objects.group_by('origin')
    #else:
    #    query = query.group_by('origin')

    context = {
        'log_messages': query,
        'tfrom': tfrom_param,
        'tto': tto_param,
        'priority_mode': True,
        'priority_list': None,
    }
    return render_to_response('loggerhandler/index.html',
                                context,
                                RequestContext(request))

def statistics_reponse(request, db_access=None, param_util=None):
    account = get_account(request)
    if not account:
        return HttpResponseRedirect('/')
    if not db_access:
        db_access = DbAccess()
    if not param_util:
        param_util = ParamUtil(request, db_access)

    info_dict = _get_basic_info_dict(db_access, param_util)
    tfrom_param = info_dict.get('tfrom', None)
    tto_param = info_dict.get('tto', None)
    priority_param = info_dict.get('priority', None)
    type_param = info_dict.get('type', None)
    origin_param = info_dict.get('origin', None)
    category_param = info_dict.get('category', None)

    return render_to_response('loggerhandler/index.html',
                                info_dict,
                                RequestContext(request))

def log_response(request, db_access=None, param_util=None):
    account = get_account(request)
    if not account:
        return HttpResponseRedirect('/')
    if not db_access:
        db_access = DbAccess()
    if not param_util:
        param_util = ParamUtil(request, db_access)
    info_dict = _get_basic_info_dict(db_access, param_util)

    type_param = info_dict.get('type', None)
    origin_param = info_dict.get('origin', None)
    tfrom_param = info_dict.get('tfrom', None)
    tto_param = info_dict.get('tto', None)
    priority_param = info_dict.get('priority', None)
    
    query = None
    if type_param:
        query = LogMessage.objects.filter(type__type=type_param)
    if origin_param:
        if not query:
            query = LogMessage.objects.filter(origin__origin=origin_param)
        else:
            query = query.filter(origin__origin=origin_param)
    if tfrom_param:
        if not query:
            query = LogMessage.objects.filter(time__gte=tfrom_param)
        else:
            query = query.filter(time__gte=tfrom_param)
    if tto_param:
        if not query:
            query = LogMessage.objects.filter(time__lte=tto_param)
        else:
            query = query.filter(time__lte=tto_param)
    if priority_param:
        if not query:
            query = LogMessage.objects.filter(
                                    newpriority__priority=priority_param)
        else:
            query = query.filter(newpriority__priority=priority_param)
    if not query:
        query = LogMessage.objects.all().order_by('-time')
    else:
        query = query.order_by('-time')
    
    # Hit the database
    log_messages = query
    update_dict = {'log_messages': log_messages,
                   'tfrom': tfrom_param.strftime(DATEFORMAT),
                   'tto': tto_param.strftime(DATEFORMAT),
                   'log_mode': True
                  }
    return render_to_response('loggerhandler/index.html',
                                info_dict,
                                RequestContext(request))
    
def statistics_response(request, db_access=None, param_util=None):
    if not db_access:
        db_access = DbAccess()
    if not param_util:
        param_util = ParamUtil(request, db_access)
    info_dict = _get_basic_info_dict(db_access, param_util)

    type_param = info_dict.get('type', None)
    origin_param = info_dict.get('origin', None)
    tfrom_param = info_dict.get('tfrom', None)
    tto_param = info_dict.get('tto', None)
    priority_param = info_dict.get('priority', None)

    return render_to_response('loggerhandler/index.html',
                                info_dict,
                                RequestContext(request))
    
def exceptions_response(request):
    """
    Handler for exception-mode.
    """
    account = get_account(request)
    if not account:
        return HttpResponseRedirect('/')
    db_access = DbAccess()
    param_util = ParamUtil(request, db_access)
    info_dict = _get_basic_info_dict(db_access, param_util)
    config = ConfigParser()
    config.read(os.path.join(nav.path.sysconfdir, 'logger.conf'))
    options = config.options("priorityexceptions")
    excepts = []
    for option in options:
        newpriority = config.get("priorityexceptions", option)
        excepts.append((option, newpriority))
    info_dict['exceptions'] = excepts
    info_dict['exceptions_mode'] = True
    return render_to_response('loggerhandler/index.html',
                                info_dict,
                                RequestContext(request))


def errors_response(request):
    """
    Handler for error-mode.
    """
    account = get_account(request)
    if not account:
        return HttpResponseRedirect('/')
    db_access = DbAccess()
    param_util = ParamUtil(request, db_access)
    info_dict = _get_basic_info_dict(db_access, param_util)
    errs = []
    for err in ErrorError.objects.all():
        errs.append(err.message)
    info_dict['errors'] = errs
    info_dict['errors_count'] = len(errs)
    info_dict['errors_mode'] = True
    return render_to_response('loggerhandler/index.html',
                                info_dict,
                                RequestContext(request))
