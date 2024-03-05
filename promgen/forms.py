# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import re
from functools import partial

from dateutil import parser
from django import forms
from django.core.exceptions import ValidationError

from promgen import errors, models, plugins, prometheus, validators


class ImportConfigForm(forms.Form):
    def _choices():
        return [("", "<Default>")] + sorted(
            (shard.name, "Import into: " + shard.name) for shard in models.Shard.objects.all()
        )

    config = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 5, "class": "form-control"}), required=False
    )
    url = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}), required=False)
    file_field = forms.FileField(
        widget=forms.FileInput(attrs={"class": "form-control"}), required=False
    )

    shard = forms.ChoiceField(choices=_choices, required=False)


class ImportRuleForm(forms.Form):
    rules = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 5, "class": "form-control"}), required=False
    )
    file_field = forms.FileField(
        widget=forms.FileInput(attrs={"class": "form-control"}), required=False
    )

    def clean(self):
        if any(self.cleaned_data.values()):
            return self.cleaned_data
        raise forms.ValidationError("Must submit data or file")


class SilenceForm(forms.Form):
    duration = forms.CharField(required=False, validators=[validators.duration])
    startsAt = forms.CharField(required=False, validators=[validators.datetime])
    endsAt = forms.CharField(required=False, validators=[validators.datetime])
    comment = forms.CharField(required=False)
    createdBy = forms.CharField(required=False)

    def clean_comment(self):
        if self.cleaned_data["comment"]:
            return self.cleaned_data["comment"]
        return "Silenced from Promgen"

    def clean_createdBy(self):
        if self.cleaned_data["createdBy"]:
            return self.cleaned_data["createdBy"]
        return "Promgen"

    def clean(self):
        data = super().clean()

        # Validation for labels
        if "labels" not in self.data or not self.data["labels"]:
            raise errors.SilenceError.NOLABEL.error()

        # Users should not be able to accidentally silence a global rule without
        # setting some other labels as well.
        if "alertname" in self.data["labels"]:
            if "service" not in self.data["labels"] and "project" not in self.data["labels"]:
                rule = models.Rule.objects.get(name=self.data["labels"]["alertname"])
                if rule.content_type.model == "site":
                    raise errors.SilenceError.GLOBALSILENCE.error()

        # Once labels have been validated, we want to add them to our cleaned data so
        # they can be submitted.
        self.cleaned_data["labels"] = self.data["labels"]

        if data.get("duration"):
            # No further validation is required if only duration is set
            return

        # Validate our start/end times
        start = data.get("startsAt")
        stop = data.get("endsAt")

        if not all([start, stop]):
            raise errors.SilenceError.STARTENDTIME.error()

        elif parser.parse(start) > parser.parse(stop):
            raise errors.SilenceError.STARTENDMISMATCH.error()


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
        exclude = ["shard"]


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
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "duration": forms.TextInput(attrs={"class": "form-control"}),
            "clause": forms.Textarea(attrs={"rows": 5, "class": "form-control"}),
            "enabled": forms.CheckboxInput(attrs={"data-toggle": "toggle", "data-size": "mini"}),
            "description": forms.Textarea(attrs={"rows": 5, "class": "form-control"}),
        }
        # We define a custom widget for each of our fields, so we just take the
        # keys here to avoid manually updating a list of fields.
        fields = widgets.keys()

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


class _KeyValueForm(forms.Form):
    key = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}))
    value = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}))


# We need a custom KeyValueSet because we need to be able to convert between the single dictionary
# form saved to our models, and the list of models used by
class _KeyValueSet(forms.BaseFormSet):
    def __init__(self, initial=None, **kwargs):
        if initial:
            kwargs["initial"] = [{"key": key, "value": initial[key]} for key in initial]
        super().__init__(**kwargs, form_kwargs={"empty_permitted": True})

    def to_dict(self):
        return {x["key"]: x["value"] for x in self.cleaned_data if x and not x["DELETE"]}


# For both LabelFormSet and AnnotationFormSet we always want to have a prefix assigned, but it's
# awkward if we need to specify it in multiple places. We use a partial here, so that it is the same
# as always passing prefix as part of our __init__ call.
LabelFormSet = partial(
    forms.formset_factory(
        form=_KeyValueForm,
        formset=_KeyValueSet,
        can_delete=True,
        extra=1,
    ),
    prefix="labels",
)

AnnotationFormSet = partial(
    forms.formset_factory(
        form=_KeyValueForm,
        formset=_KeyValueSet,
        can_delete=True,
        extra=1,
    ),
    prefix="annotations",
)


class RuleCopyForm(forms.Form):
    content_type = forms.ChoiceField(choices=[(x, x) for x in ["service", "project"]])
    object_id = forms.IntegerField()


class FarmForm(forms.ModelForm):
    class Meta:
        model = models.Farm
        exclude = ["source"]


class SenderForm(forms.ModelForm):
    sender = forms.ChoiceField(
        choices=[(entry.module_name, entry.module_name) for entry in plugins.notifications()]
    )

    class Meta:
        model = models.Sender
        exclude = ["content_type", "object_id", "owner", "enabled"]


class NotifierUpdate(forms.ModelForm):
    class Meta:
        model = models.Sender
        exclude = ["value"]


class HostForm(forms.Form):
    hosts = forms.CharField(widget=forms.Textarea)

    def clean(self):
        # Hosts may be submitted delimiated by either , or newline so
        # once we split on that, we want to make sure there are no invalid
        # hostnames
        hosts = set()
        for hostname in re.split(r"[,\s]+", self.cleaned_data["hosts"]):
            if hostname == "":
                continue
            validators.hostname(hostname)
            hosts.add(hostname)
        if not hosts:
            raise ValidationError("No valid hosts")
        self.cleaned_data["hosts"] = list(hosts)
