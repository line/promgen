promgen/forms.pyimport datetime
from django import forms

from promgen import models, plugins


class ImportForm(forms.Form):
    config = forms.CharField(widget=forms.Textarea, required=False)
    url = forms.CharField(required=False)
    file_field = forms.FileField(required=False)


class MuteForm(forms.Form):
    next = forms.CharField(required=False)
    duration = forms.CharField(required=False)
    duration_from = forms.CharField(required=False)
    duration_to = forms.CharField(required=False)

    def clean_duration_from(self):
        try:
            datetime.datetime.strptime(self.data.get('duration_start', ''), '%Y-%m-%d %H:%M')
        except Exception as e:
            raise forms.ValidationError('Please enter one of them')

    def clean(self):
        duration = self.data.get('duration', '')
        duration_from = self.data.get('duration_from', '')
        duration_to = self.data.get('duration_to', '')

        if not duration \
                and not duration_from \
                and not duration_to:
            raise forms.ValidationError('Please enter one of them')

        dt = {}
        for str in [duration_from, duration_to]:
            if str:
                try:
                    dt[str] = datetime.datetime.strptime(str, '%Y-%m-%d %H:%M')
                except Exception as e:
                    raise forms.ValidationError('Datetime format error')

        if duration_from:
            if not duration_to:
                raise forms.ValidationError('Enter start, end is required')

            if dt[duration_from] > dt[duration_to]:
                raise forms.ValidationError('End is error')


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


class RuleCopyForm(forms.Form):
    rule_id = forms.TypedChoiceField(coerce=int, choices=[
        (rule.pk, rule.name) for rule in models.Rule.objects.all()
    ])


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
        exclude = ['content_type', 'object_id']


class HostForm(forms.Form):
    hosts = forms.CharField(widget=forms.Textarea)
