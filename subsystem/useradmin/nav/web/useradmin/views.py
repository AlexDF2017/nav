# -*- coding: utf-8 -*-
#
# Copyright 2008 UNINETT AS
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

__copyright__ = "Copyright 2008 UNINETT AS"
__license__ = "GPL"
__author__ = "Thomas Adamcik (thomas.adamcik@uninett.no)"
__id__ = "$Id$"

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, get_list_or_404
from django.template import RequestContext

from nav.models.profiles import Account, AccountGroup
from nav.django.shortcuts import render_to_response, object_list, object_detail

from nav.web.message import new_message, Messages
from nav.web.templates.UserAdmin import UserAdmin
from nav.web.useradmin.forms import *
from nav.django.context_processors import account_processor

# FIXME make this global
class UserAdminContext(RequestContext):
    def __init__(self, *args, **kwargs):
        if 'processors' not in kwargs:
            kwargs['processors'] = [account_processor]
        super(UserAdminContext, self).__init__(*args, **kwargs)

def account_list(request):
    return object_list(UserAdmin, request, Account.objects.all(),
                        template_object_name='account',
                        template_name='useradmin/account_list.html',
                        extra_context={'active': {'account_list': 1}},
                        context_processors=[account_processor])

def account_detail(request, account_id=None):
    try:
        account = Account.objects.get(id=account_id)
    except Account.DoesNotExist:
        account = None

    account_form = AccountForm(instance=account)
    org_form = OrganizationAddForm()
    group_form = GroupAddForm()

    if request.method == 'POST':
        if 'submit_account' in request.POST:
            account_form = AccountForm(request.POST, instance=account)

            if account_form.is_valid():
                account = account_form.save(commit=False)

                if 'password1' in account_form.cleaned_data and not account.ext_sync:
                    account.set_password(account_form.cleaned_data['password1'])

                account.save()

                new_message(request, '"%s" has been saved.' % (account), type=Messages.SUCCESS)
                return HttpResponseRedirect(reverse('useradmin-account_detail', args=[account.id]))

        elif 'submit_org' in request.POST:
            org_form = OrganizationAddForm(request.POST)

            if org_form.is_valid():
                organization = org_form.cleaned_data['organization']
                account.organizations.add(organization)

                new_message(request, 'Added organization "%s" to account "%s"' % (organization, account), type=Messages.SUCCESS)
                return HttpResponseRedirect(reverse('useradmin-account_detail', args=[account.id]))

        elif 'submit_group' in request.POST:
            group_form = GroupAddForm(request.POST)

            if group_form.is_valid():
                group = group_form.cleaned_data['group']
                account.accountgroup_set.add(group)
                account.save()

                new_message(request, 'Added "%s" to group "%s"' % (account, group), type=Messages.SUCCESS)
                return HttpResponseRedirect(reverse('useradmin-account_detail', args=[account.id]))

    if account:
        active = {'account_detail': True}
    else:
        active = {'account_new': True}

    return render_to_response(UserAdmin, 'useradmin/account_detail.html',
                        {
                            'active': active,
                            'account': account,
                            'account_form': account_form,
                            'org_form': org_form,
                            'group_form': group_form,
                        }, UserAdminContext(request))

def account_delete(request, account_id):
    try:
        account = Account.objects.get(id=account_id)
    except Account.DoesNotExist:
        new_message(request, 'Account %s does not exist.' % (account_id), type=Messages.ERROR)
        return HttpResponseRedirect(reverse('useradmin-account_list'))

    if account.is_system_account():
        new_message(request, 'Account %s can not be deleted as it is a system account.' % (account.name), type=Messages.ERROR)
        return HttpResponseRedirect(reverse('useradmin-account_detail', args=[account.id]))

    if request.method == 'POST':
        account.delete()
        new_message(request, 'Account %s has been deleted.' % (account.name), type=Messages.SUCCESS)
        return HttpResponseRedirect(reverse('useradmin-account_list'))

    return render_to_response(UserAdmin, 'useradmin/delete.html',
                        {
                            'name': '%s (%s)' % (account.name, account.login),
                            'type': 'account',
                        }, UserAdminContext(request))

def account_organization_remove(request, account_id, org_id):
    try:
        account = Account.objects.get(id=account_id)
    except Account.DoesNotExist:
        new_message(request, 'Account %s does not exist.' % (account_id), type=Messages.ERROR)
        return HttpResponseRedirect(reverse('useradmin-account_list'))

    try:
        organization = account.organizations.get(id=org_id)
    except Organization.DoesNotExist:
        new_message(request, 'Organization %s does not exist or it is not associated with %s.' % (org_id, account), type=Messages.ERROR)
        return HttpResponseRedirect(reverse('useradmin-account_detail', args=[account.id]))

    if request.method == 'POST':
        account.organizations.remove(organization)
        new_message(request, 'Organization %s has been removed from account %s.' % (organization, account), type=Messages.SUCCESS)
        return HttpResponseRedirect(reverse('useradmin-account_detail', args=[account.id]))

    return render_to_response(UserAdmin, 'useradmin/delete.html',
                        {
                            'name': '%s from %s' % (organization, account),
                            'type': 'organization',
                        }, UserAdminContext(request))

def account_group_remove(request, account_id, group_id, missing_redirect=None, plain_redirect=None):
    try:
        account = Account.objects.get(id=account_id)
    except Account.DoesNotExist:
        new_message(request, 'Account %s does not exist.' % (account_id), type=Messages.ERROR)

        if missing_redirect:
            return HttpResponseRedirect(missing_redirect)
        return HttpResponseRedirect(reverse('useradmin-account_list'))

    try:
        group = account.accountgroup_set.get(id=group_id)
    except AccountGroup.DoesNotExist:
        new_message(request, 'Group %s does not exist or it is not associated with %s.' % (group_id, account), type=Messages.WARNING)

        if plain_redirect:
            return HttpResponseRedirect(plain_redirect)
        return HttpResponseRedirect(reverse('useradmin-account_detail', args=[account.id]))

    if request.method == 'POST':
        account.accountgroup_set.remove(group)
        new_message(request, '%s has been removed from %s.' % (account, group), type=Messages.SUCCESS)

        if plain_redirect:
            return HttpResponseRedirect(plain_redirect)
        return HttpResponseRedirect(reverse('useradmin-account_detail', args=[account.id]))

    return render_to_response(UserAdmin, 'useradmin/delete.html',
                        {
                            'name': '%s from the group %s' % (account, group),
                            'type': 'account',
                        }, UserAdminContext(request))


def group_list(request):
    return object_list(UserAdmin, request, AccountGroup.objects.all(),
                        template_object_name='group',
                        template_name='useradmin/group_list.html',
                        extra_context={'active': {'group_list': 1}})

def group_detail(request, group_id=None):
    try:
        group = AccountGroup.objects.get(id=group_id)
    except AccountGroup.DoesNotExist:
        group = None

    group_form = AccountGroupForm(instance=group)
    account_form = AccountAddForm()
    privilege_form = PrivilegeForm()

    if request.method == 'POST':

        if 'submit_group' in request.POST:
            group_form = AccountGroupForm(request.POST, instance=group)

            if group_form.is_valid():
                group_form.save()

                new_message(request, '"%s" has been saved.' % (group), type=Messages.SUCCESS)
                return HttpResponseRedirect(reverse('useradmin-group_detail', args=[group.id]))

        elif 'submit_privilege' in request.POST:
            privilege_form = PrivilegeForm(request.POST)

            if privilege_form.is_valid():
                type = privilege_form.cleaned_data['type']
                target = privilege_form.cleaned_data['target']

                try:
                    group.privilege_set.get(type=type, target=target)
                    new_message(request, 'Privilege was not added as it allready exists.', type=Messages.WARNING)
                except Privilege.DoesNotExist:
                    group.privilege_set.create(type=type, target=target)
                    new_message(request, 'Privilege has been added.', type=Messages.SUCCESS)

                return HttpResponseRedirect(reverse('useradmin-group_detail', args=[group.id]))
        elif 'submit_account' in request.POST:
            account_form = AccountAddForm(request.POST)

            if account_form.is_valid():
                try:
                    account = account_form.cleaned_data['account']
                    group.accounts.get(login=account.login)
                    new_message(request, 'Account %s was not added as it is allready a member of the group.' % account, type=Messages.WARNING)
                except Account.DoesNotExist:
                    group.accounts.add(account)
                    new_message(request, 'Account %s has been added.' % account, type=Messages.SUCCESS)

                return HttpResponseRedirect(reverse('useradmin-group_detail', args=[group.id]))

    if group:
        active = {'group_detail': True}
    else:
        active = {'group_new': True}

    return render_to_response(UserAdmin, 'useradmin/group_detail.html',
                        {
                            'active': active,
                            'group': group,
                            'group_form': group_form,
                            'account_form': account_form,
                            'privilege_form': privilege_form,
                        }, UserAdminContext(request))

def group_delete(request, group_id):
    pass

def group_account_remove(request, group_id, account_id):
    return account_group_remove(request, account_id, group_id,
            missing_redirect=reverse('useradmin-group_list'),
            plain_redirect=reverse('useradmin-group_detail', args=[group_id]))

def group_privilege_remove(request, group_id, privilege_id):
    pass
