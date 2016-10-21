from django import forms

from promgen import models


class ExporterForm(forms.Form):
    job = forms.CharField()
    port = forms.IntegerField()
    path = forms.CharField(required=False)
    project_id = forms.HiddenInput()


class ProjectForm(forms.Form):
    name = forms.CharField()
    service_id = forms.HiddenInput()


class RuleForm(forms.ModelForm):
    class Meta:
        model = models.Rule
        exclude = ['service']


class FarmForm(forms.ModelForm):
    class Meta:
        model = models.Farm
        exclude = ['source']


class SenderForm(forms.ModelForm):
    class Meta:
        model = models.Sender
        exclude = ['project']


class HostForm(forms.Form):
    hosts = forms.CharField(widget=forms.Textarea)
