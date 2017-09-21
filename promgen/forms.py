# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import datetime

from django import forms

from promgen import models, plugins


class ImportConfigForm(forms.Form):
    def _choices():
        return [('', '<Default>')] + sorted([(shard.name, 'Import into: ' + shard.name) for shard in models.Shard.objects.all()])

    config = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
        required=False)
    url = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False)
    file_field = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        required=False)

    shard = forms.ChoiceField(choices=_choices, required=False)


class ImportRuleForm(forms.Form):
    rules = forms.CharField(widget=forms.Textarea, required=True)


class SilenceForm(forms.Form):
    def validate_datetime(value):
        try:
            datetime.datetime.strptime(value, '%Y-%m-%d %H:%M')
        except:
            raise forms.ValidationError('Invalid timestamp')

    next = forms.CharField(required=False)
    duration = forms.CharField(required=False)
    start = forms.CharField(required=False, validators=[validate_datetime])
    stop = forms.CharField(required=False, validators=[validate_datetime])
    comment = forms.CharField(required=False)
    created_by = forms.CharField(required=False)

    def clean_comment(self):
        if self.cleaned_data['comment']:
            return self.cleaned_data['comment']
        return "Silenced from Promgen"

    def clean_created_by(self):
        if self.cleaned_data['created_by']:
            return self.cleaned_data['created_by']
        return "Promgen"

    def clean(self):
        duration = self.data.get('duration')
        start = self.data.get('start')
        stop = self.data.get('stop')

        if duration:
            # No further validation is required if only duration is set
            return

        if not all([start, stop]):
            raise forms.ValidationError('Both start and end are required')
        elif datetime.datetime.strptime(start, '%Y-%m-%d %H:%M') > datetime.datetime.strptime(stop, '%Y-%m-%d %H:%M'):
            raise forms.ValidationError('Start time and end time is mismatch')


class SilenceExpireForm(forms.Form):
    silence_id = forms.CharField(required=True)
    next = forms.CharField(required=False)


class ExporterForm(forms.ModelForm):
    class Meta:
        model = models.Exporter
        exclude = ['project']

        widgets = {
            'job': forms.TextInput(attrs={'class': 'form-control'}),
            'port': forms.TextInput(attrs={'class': 'form-control', 'type': 'number'}),
            'path': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '/metrics'}),
        }


class ServiceForm(forms.ModelForm):
    class Meta:
        model = models.Service
        exclude = []


class ProjectForm(forms.ModelForm):
    class Meta:
        model = models.Project
        exclude = ['service', 'farm']


class ProjectMove(forms.ModelForm):
    class Meta:
        model = models.Project
        exclude = ['farm']


class URLForm(forms.ModelForm):
    class Meta:
        model = models.URL
        exclude = ['project']


class NewRuleForm(forms.ModelForm):
    class Meta:
        model = models.Rule
        exclude = ['content_type', 'object_id', 'parent']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'duration': forms.TextInput(attrs={'class': 'form-control'}),
            'clause': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
            'enabled': forms.CheckboxInput(attrs={'data-toggle': 'toggle', 'data-size': 'mini'})
        }


class RuleForm(forms.ModelForm):
    class Meta:
        model = models.Rule
        exclude = ['parent', 'content_type', 'object_id']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'duration': forms.TextInput(attrs={'class': 'form-control'}),
            'clause': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
            'enabled': forms.CheckboxInput(attrs={'data-toggle': 'toggle', 'data-size': 'mini'})
        }


class RuleCopyForm(forms.Form):
    content_type = forms.ChoiceField(choices=[(x, x) for x in ['service', 'project']])
    object_id = forms.IntegerField()


class FarmForm(forms.ModelForm):
    class Meta:
        model = models.Farm
        exclude = ['source']


class SenderForm(forms.ModelForm):
    sender = forms.ChoiceField(choices=[
        (entry.module_name, entry.module_name) for entry in plugins.notifications()
    ])

    class Meta:
        model = models.Sender
        exclude = ['content_type', 'object_id', 'owner']


class HostForm(forms.Form):
    hosts = forms.CharField(widget=forms.Textarea)
