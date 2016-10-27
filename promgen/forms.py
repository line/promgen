from django import forms
from pkg_resources import working_set

from promgen import models


class ImportForm(forms.Form):
    config = forms.CharField(widget=forms.Textarea, required=False)
    url = forms.CharField(required=False)
    file_field = forms.FileField(required=False)


class ExporterForm(forms.ModelForm):
    class Meta:
        model = models.Exporter
        exclude = ['project']


class ServiceForm(forms.ModelForm):
    class Meta:
        model = models.Service
        exclude = []


class ProjectForm(forms.ModelForm):
    class Meta:
        model = models.Project
        exclude = ['service', 'farm']


class RuleForm(forms.ModelForm):
    class Meta:
        model = models.Rule
        exclude = ['service']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'clause': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
            'labels': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
            'annotations': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
        }


class FarmForm(forms.ModelForm):
    class Meta:
        model = models.Farm
        exclude = ['source']


class SenderForm(forms.ModelForm):
    sender = forms.ChoiceField(choices=[
        (entry.module_name, entry.module_name) for entry in working_set.iter_entry_points('promgen.sender')
    ])

    class Meta:
        model = models.Sender
        exclude = ['project']


class HostForm(forms.Form):
    hosts = forms.CharField(widget=forms.Textarea)
