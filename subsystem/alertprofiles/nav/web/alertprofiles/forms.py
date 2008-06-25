# -*- coding: utf-8 -*-
#
# Copyright 2007-2008 UNINETT AS
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
# Authors: Magnus Motzfeldt Eide <magnus.eide@uninett.no>
#

__copyright__ = "Copyright 2008 UNINETT AS"
__license__ = "GPL"
__author__ = "Magnus Motzfeldt Eide (magnus.eide@uninett.no)"
__id__ = "$Id$"

from django import newforms as forms

from nav.models.profiles import MatchField, Filter, Expresion

class FilterForm(forms.ModelForm):
    id = forms.IntegerField(required=False, widget=forms.widgets.HiddenInput)
    owner = forms.BooleanField(required=False, label='Private',
        help_text='Uncheck to allow all users to use this filter.')
    name = forms.CharField()

    class Meta:
        model = Filter

    def __init__(self, *args, **kwargs):
        admin = kwargs.pop('admin', None)
        super(FilterForm, self).__init__(*args, **kwargs)
        
        if not admin:
            self.fields['owner'].widget.attrs['disabled'] = 'disabled'

class MatchFieldForm(forms.ModelForm):
    class Meta:
        model = MatchField

class ExpresionForm(forms.ModelForm):
    filter = forms.IntegerField(widget=forms.widgets.HiddenInput)
    match_field = forms.IntegerField(widget=forms.widgets.HiddenInput)
    value = forms.CharField()
    class Meta:
        model = Expresion

    def __init__(self, *args, **kwargs):
        match_field = kwargs.pop('match_field', None)
        super(ExpresionForm, self).__init__(*args, **kwargs)

#        self.fields['filter'].widget.attrs['disabled'] = 'disabled'
#        self.fields['match_field'].widget.attrs['disabled'] = 'disabled'

        if isinstance(match_field, MatchField):
            operators = match_field.operator_set.all()
            self.fields['operator'] = forms.models.ChoiceField([(o.type, o) for o in operators])

            if match_field.show_list:
                model, attname = MatchField.MODEL_MAP[match_field.value_id]
                choices = [(getattr(a, attname), getattr(a, attname)) for a in model.objects.all()]

                self.fields['value'] = forms.MultipleChoiceField(choices=choices)
