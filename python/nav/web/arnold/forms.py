#
# Copyright (C) 2012 (SD -311000) UNINETT AS
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
"""Forms for Arnold"""

from IPy import IP
from django import forms
from nav.util import is_valid_ip, is_valid_mac

from nav.models.arnold import (DETENTION_TYPE_CHOICES, STATUSES,
                               KEEP_CLOSED_CHOICES, Justification,
                               QuarantineVlan, DetentionProfile)


class JustificationForm(forms.Form):
    """Form for adding a new justificaton"""
    name = forms.CharField(label="Name")
    description = forms.CharField(label="Description", required=False)
    justificationid = forms.IntegerField(widget=forms.HiddenInput(),
                                         required=False)


class QuarantineVlanForm(forms.Form):
    """Form for adding a new quarantine vlan"""
    vlan = forms.IntegerField(label="Vlan")
    description = forms.CharField(label="Description", required=False)
    qid = forms.IntegerField(widget=forms.HiddenInput(),
                             required=False)


class HistorySearchForm(forms.Form):
    """Form for searching in history"""
    days = forms.IntegerField(widget=forms.TextInput({'size': 3}))


class SearchForm(forms.Form):
    """Form for searching for detained computers"""
    search_choices = [('ip', 'IP'), ('mac', 'MAC'), ('netbios', 'Netbios'),
                      ('dns', 'DNS')]
    status_choices = STATUSES + [('any', 'Any')]

    searchtype = forms.ChoiceField(choices=search_choices)
    searchvalue = forms.CharField(required=True)
    status = forms.ChoiceField(choices=status_choices, label='Status')
    days = forms.IntegerField(label='Days',
                              widget=forms.TextInput({'size': 3}))

    def clean_searchvalue(self):
        """Clean whitespace from searchvalue"""
        return self.cleaned_data['searchvalue'].strip()

    def clean(self):
        """Validate on several fields"""
        cleaned_data = self.cleaned_data
        searchtype = cleaned_data.get('searchtype')
        searchvalue = cleaned_data.get('searchvalue')

        if searchtype == 'ip':
            try:
                IP(searchvalue)
            except ValueError:
                self._errors["searchvalue"] = self.error_class(
                    ["IP-address or range is not valid"])
                del cleaned_data["searchvalue"]

        return cleaned_data


class DetentionProfileForm(forms.Form):
    """Form for creating a new detention profile"""

    detention_id = forms.IntegerField(widget=forms.HiddenInput(),
                                      required=False)
    detention_type = forms.ChoiceField(choices=DETENTION_TYPE_CHOICES,
                                       widget=forms.RadioSelect(),
                                       initial=DETENTION_TYPE_CHOICES[0][0])
    title = forms.CharField(label="Title")
    description = forms.CharField(label="Description", widget=forms.Textarea,
                                  required=False)
    justification = forms.ChoiceField(label="Reason")
    qvlan = forms.ChoiceField(label="Quarantinevlan", required=False)
    mail = forms.CharField(label="Path to mailfile", required=False)
    keep_closed = forms.ChoiceField(label="Detention pursuit",
                                    choices=KEEP_CLOSED_CHOICES,
                                    widget=forms.RadioSelect(),
                                    initial=KEEP_CLOSED_CHOICES[0][0])
    exponential = forms.BooleanField(label="Exponential increase",
                                     required=False)
    duration = forms.IntegerField(label="Detention duration")
    active_on_vlans = forms.CharField(label="Active on vlans", required=False)
    active = forms.BooleanField(label="Active", required=False)

    def clean(self):
        cleaned_data = self.cleaned_data
        detention_type = cleaned_data.get('detention_type')
        qvlan = cleaned_data.get('qvlan')

        # If method = quarantine and no quarantine vlan is set, throw error
        if detention_type == DETENTION_TYPE_CHOICES[1][0] and not qvlan:
            self._errors['qvlan'] = self.error_class(
                ['This field is required'])
            del cleaned_data['qvlan']

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super(DetentionProfileForm, self).__init__(*args, **kwargs)
        self.fields['qvlan'].choices = get_quarantine_vlans()
        did = self.data.get('detention_id') or self.initial.get(
            'detention_id')
        self.fields['justification'].choices = get_justifications(did)


class ManualDetentionTargetForm(forms.Form):
    """Form for step one of manual detention"""
    target = forms.CharField(label="IP/MAC to detain")

    def clean_target(self):
        """Validate target"""
        target = self.cleaned_data['target'].strip()
        if not (is_valid_ip(target) or is_valid_mac(target)):
            raise forms.ValidationError('Not a valid ip or mac-address')

        return target


class ManualDetentionForm(forms.Form):
    """Form for executing a manual detention"""

    method = forms.ChoiceField(label="Choose method",
                               choices=DETENTION_TYPE_CHOICES,
                               initial=DETENTION_TYPE_CHOICES[0][0],
                               widget=forms.RadioSelect())
    target = forms.CharField(label="IP/MAC to detain",
                             widget=forms.TextInput(attrs={'readonly': True}))
    camtuple = forms.ChoiceField(label="Interface")
    justification = forms.ChoiceField(label="Reason")
    qvlan = forms.ChoiceField(label="Quarantine vlan", required=False)
    comment = forms.CharField(label="Comment", required=False)
    days = forms.IntegerField(label="Autoenable in", required=False)

    def clean(self):
        cleaned_data = self.cleaned_data
        method = cleaned_data.get('method')
        qvlan = cleaned_data.get('qvlan')

        # If method = quarantine and no quarantine vlan is set, throw error
        if method == 'quarantine' and not qvlan:
            self._errors['qvlan'] = self.error_class(
                ['This field is required'])
            del cleaned_data['qvlan']

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super(ManualDetentionForm, self).__init__(*args, **kwargs)
        self.fields['justification'].choices = get_justifications()
        self.fields['qvlan'].choices = get_quarantine_vlans()


def get_justifications(profileid=None):
    """Return list of justifications ready for use as choices in forms

    Justifications used in detention profiles must not be listed. If
    profileid is given, make sure the justification for that profile is added.

    """
    if profileid:
        detention_profiles = DetentionProfile.objects.exclude(id=profileid)
    else:
        detention_profiles = DetentionProfile.objects.all()

    justifications = detention_profiles.values_list('justification')
    return [('', '-- Select reason --')] +\
           [(j.id, j.name) for j in Justification.objects.exclude(
               id__in=justifications)]


def get_quarantine_vlans():
    """Return list of quarantine vlans ready for use as choices in form"""
    return [('', '-- Select vlan --')] + [(q.id,
                                           str(q)) for q in
                                          QuarantineVlan.objects.all()]