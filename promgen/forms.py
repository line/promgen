from django import forms

from promgen import models, plugins


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


class URLForm(forms.ModelForm):
    class Meta:
        model = models.URL
        exclude = ['project']


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
        (entry.module_name, entry.module_name) for entry in plugins.senders()
    ])

    class Meta:
        model = models.Sender
        exclude = ['project']


class HostForm(forms.Form):
    hosts = forms.CharField(widget=forms.Textarea)
