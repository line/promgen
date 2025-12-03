# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import re
from functools import partial

from dateutil import parser
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from guardian.conf.settings import ANONYMOUS_USER_NAME
from guardian.shortcuts import get_perms_for_model

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

        # In Django https://code.djangoproject.com/ticket/19580, some of the
        # foreign key checks got stricter. We sets pk to 0 here so that it passes
        # django's m2m/foreign key checks, but marks for us that it's a temporary
        # rule that doesn't actually exist.
        # We'll likely want to rework this assumption when we move to a different
        # promql check
        rule.pk = 0

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
        exclude = ["source", "project"]


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


def get_permission_choices(input_object):
    permissions = get_perms_for_model(input_object)
    for permission in permissions.filter(name__in=["Admin", "Editor", "Viewer", "Member"]):
        yield (permission.codename, permission.name)


def get_group_choices():
    yield ("", "")
    for g in models.Group.objects.exclude(name=settings.PROMGEN_DEFAULT_GROUP).order_by("name"):
        yield (g.name, g.name)


def get_user_choices():
    # Add an empty choice to trigger the Select2 placeholder
    yield ("", "")

    for u in (
        User.objects.filter(is_active=True)
        .exclude(username=ANONYMOUS_USER_NAME)
        .order_by("username")
    ):
        if u.first_name:
            yield (u.username, f"{u.username} ({u.first_name} {u.last_name})")
        elif u.email:
            yield (u.username, f"{u.username} ({u.email})")
        else:
            yield (u.username, u.username)


class UserPermissionForm(forms.Form):
    permission = forms.ChoiceField(
        required=True,
        label="Role",
    )

    username = forms.ChoiceField(
        required=False,
        label="Username",
    )

    group = forms.ChoiceField(
        required=False,
        label="Group",
    )

    def __init__(self, *args, **kwargs):
        input_object = kwargs.pop("input_object", None)
        super(UserPermissionForm, self).__init__(*args, **kwargs)
        if input_object:
            self.fields["permission"].choices = get_permission_choices(input_object)
        self.fields["username"].choices = get_user_choices()
        self.fields["group"].choices = get_group_choices()


class GroupMemberForm(forms.Form):
    permission = forms.ChoiceField(
        required=True,
        label="Role",
    )

    users = forms.MultipleChoiceField(
        required=True,
        label="Users",
    )

    def __init__(self, *args, **kwargs):
        input_object = kwargs.pop("input_object", None)
        super(GroupMemberForm, self).__init__(*args, **kwargs)
        if input_object:
            self.fields["permission"].choices = get_permission_choices(input_object)
        self.fields["users"].choices = get_user_choices()


class UserMergeForm(forms.Form):
    user_to_merge_from = forms.ChoiceField(required=True)
    user_to_merge_into = forms.ChoiceField(required=True)

    def __init__(self, *args, **kwargs):
        super(UserMergeForm, self).__init__(*args, **kwargs)
        self.fields["user_to_merge_from"].choices = get_user_choices()
        self.fields["user_to_merge_from"].label = _(
            "User to merge from (This account will be deleted)"
        )
        self.fields["user_to_merge_into"].choices = get_user_choices()
        self.fields["user_to_merge_into"].label = _(
            "User to merge into (This account will be kept)"
        )

    def clean(self):
        cleaned_data = super().clean()
        user_to_merge_from = cleaned_data.get("user_to_merge_from")
        user_to_merge_into = cleaned_data.get("user_to_merge_into")

        if user_to_merge_from == user_to_merge_into:
            raise ValidationError(
                _("The user to merge from and the user to merge into must be different.")
            )

        return cleaned_data
