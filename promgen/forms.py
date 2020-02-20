# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import re

from dateutil import parser

from promgen import models, plugins, prometheus, validators

from django import forms
from django.core.exceptions import ValidationError


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
    rules = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
        required=False)
    file_field = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        required=False)


class SilenceForm(forms.Form):

    duration = forms.CharField(required=False, validators=[validators.duration])
    startsAt = forms.CharField(required=False, validators=[validators.datetime])
    endsAt = forms.CharField(required=False, validators=[validators.datetime])
    comment = forms.CharField(required=False)
    createdBy = forms.CharField(required=False)

    def clean_comment(self):
        if self.cleaned_data['comment']:
            return self.cleaned_data['comment']
        return "Silenced from Promgen"

    def clean_createdBy(self):
        if self.cleaned_data['createdBy']:
            return self.cleaned_data['createdBy']
        return "Promgen"

    def clean(self):
        duration = self.data.get('duration')
        start = self.data.get('startsAt')
        stop = self.data.get('endsAt')

        if duration:
            # No further validation is required if only duration is set
            return

        if not all([start, stop]):
            raise forms.ValidationError('Both start and end are required')
        elif parser.parse(start) > parser.parse(stop):
            raise forms.ValidationError('Start time and end time is mismatch')


class SilenceExpireForm(forms.Form):
    silence_id = forms.CharField(required=True)
    next = forms.CharField(required=False)


class ExporterForm(forms.ModelForm):
    class Meta:
        model = models.Exporter
        exclude = ["project"]

        widgets = {
            "job": forms.TextInput(attrs={"class": "form-control"}),
            "port": forms.TextInput(attrs={"class": "form-control", "type": "number"}),
            "path": forms.TextInput(attrs={"class": "form-control", "placeholder": "/metrics"}),
            "scheme": forms.Select(attrs={"class": "form-control"}),
        }


class ServiceRegister(forms.ModelForm):
    class Meta:
        model = models.Service
        # shard is determined by the pk in the service register url
        exclude = ['shard']


class ServiceUpdate(forms.ModelForm):
    class Meta:
        model = models.Service
        exclude = []


class URLForm(forms.ModelForm):
    class Meta:
        model = models.URL
        fields = ["url", "probe"]
        widgets = {
            "url": forms.TextInput(attrs={"class": "form-control input-sm"}),
            "probe": forms.Select(attrs={"class": "form-control input-sm"}),
        }


class AlertRuleForm(forms.ModelForm):
    class Meta:
        model = models.Rule
        exclude = ['parent', 'content_type', 'object_id']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'duration': forms.TextInput(attrs={'class': 'form-control'}),
            'clause': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
            'enabled': forms.CheckboxInput(attrs={'data-toggle': 'toggle', 'data-size': 'mini'}),
            'description': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
        }

    def clean(self):
        # Check our cleaned data then let Prometheus check our rule
        super().clean()
        rule = models.Rule(**self.cleaned_data)
        
        # Make sure we pull in our labels and annotations for
        # testing if needed
        # See django docs on cached_property
        rule.labels = self.instance.labels
        rule.annotations = self.instance.annotations

        prometheus.check_rules([rule])


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


class NotifierUpdate(forms.ModelForm):
    class Meta:
        model = models.Sender
        exclude = ['value']


class HostForm(forms.Form):
    hosts = forms.CharField(widget=forms.Textarea)

    def clean(self):
        # Hosts may be submitted delimiated by either , or newline so
        # once we split on that, we want to make sure there are no invalid
        # hostnames
        hosts = set()
        for hostname in re.split("[,\s]+", self.cleaned_data["hosts"]):
            if hostname == "":
                continue
            if ":" in hostname:
                raise ValidationError("Invalid hostname %s" % hostname)
            hosts.add(hostname)
        if not hosts:
            raise ValidationError("No valid hosts")
        self.cleaned_data["hosts"] = list(hosts)


LabelFormset = forms.inlineformset_factory(
    models.Rule,
    models.RuleLabel,
    fields=("name", "value"),
    widgets={
        "name": forms.TextInput(attrs={"class": "form-control"}),
        "value": forms.TextInput(attrs={"rows": 5, "class": "form-control"}),
    },
)


AnnotationFormset = forms.inlineformset_factory(
    models.Rule,
    models.RuleAnnotation,
    fields=("name", "value"),
    widgets={
        "name": forms.TextInput(attrs={"class": "form-control"}),
        "value": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
    },
)
