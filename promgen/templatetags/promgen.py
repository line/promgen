# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import collections
import difflib
import json
from datetime import datetime
from urllib.parse import urlencode

import yaml
from django import template
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from guardian.shortcuts import get_groups_with_perms, get_users_with_perms

register = template.Library()

EXCLUSION_MACRO = "<exclude>"


@register.filter()
def klass(value):
    return value.__class__.__name__


@register.filter()
def rule_dict(rule):
    return {
        "alert": rule.name,
        "expr": rulemacro(rule),
        "for": rule.duration,
        "labels": rule.labels,
        "annotations": rule.annotations,
    }


@register.filter()
def rulemacro(rule, clause=None):
    """
    Macro rule expansion

    Assuming a list of rules with children and parents, expand our macro to exclude child rules

    Can optionally pass expression to render in the context of the passed rule

    .. code-block:: none

        foo{<exclude>} / bar{<exclude>} > 5 # Parent Rule
        foo{project="A", <exclude>} / bar{project="A", <exclude>} > 3 # Child Rule
        foo{project="B"} / bar{project="B"} > 4 # Child Rule

        foo{project~="A|B"} / bar{project~="A|B"} > 5
        foo{project="A", } / bar{project="A"} > 3
        foo{project="B"} / bar{project="B"} > 4
    """

    if not clause:
        clause = rule.clause

    labels = collections.defaultdict(list)
    for r in rule.overrides.all():
        labels[r.content_type.model].append(r.content_object.name)

    filters = {k: "|".join(labels[k]) for k in sorted(labels)}
    macro = ",".join(sorted(f'{k}!~"{v}"' for k, v in filters.items()))
    return clause.replace(EXCLUSION_MACRO, macro)


@register.simple_tag
def diff_json(a, b):
    if isinstance(a, str):
        a = json.loads(a)
    if isinstance(b, str):
        b = json.loads(b)
    a = json.dumps(a, indent=4, sort_keys=True).splitlines(keepends=True)
    b = json.dumps(b, indent=4, sort_keys=True).splitlines(keepends=True)
    diff = "".join(difflib.unified_diff(a, b))
    if diff:
        return diff
    return "No Changes"


@register.filter()
def pretty_json(data):
    if isinstance(data, str):
        data = json.loads(data)
    return json.dumps(data, indent=4, sort_keys=True)


@register.filter()
def pretty_yaml(data):
    return yaml.safe_dump(data)


@register.filter()
def strftime(timestamp, fmt):
    """
    Convert a timestamp to a specific format.

    Normally we would use the built in django `time` filters, but sometimes we
    get a numeric value as a timestamp (from Prometheus results) so we want a
    single place where we can convert any type of value to a timestamp.
    """
    if isinstance(timestamp, int) or isinstance(timestamp, float):
        dt = datetime.fromtimestamp(timestamp, timezone.utc)
        return timezone.localtime(dt).strftime(fmt)
    return timestamp


@register.simple_tag
def breadcrumb(instance=None, label=None):
    """
    Create HTML Breadcrumb from instance

    Starting with the instance, walk up the tree building a bootstrap3
    compatible breadcrumb
    """
    from promgen import models

    def site(obj):
        yield reverse("site-detail"), obj.domain

    def shard(obj):
        yield reverse("datasource-list"), _("Datasource")
        yield obj.get_absolute_url(), obj.name

    def service(obj):
        yield reverse("service-list"), _("Services")
        yield obj.get_absolute_url(), obj.name

    def project(obj):
        yield from service(obj.service)
        yield obj.get_absolute_url(), obj.name

    def alert(obj):
        yield reverse("alert-list"), _("Alerts")
        yield obj.get_absolute_url(), obj.pk

    def rule(obj):
        if obj.content_type.model == "site":
            yield from site(obj.content_object)
        if obj.content_type.model == "service":
            yield from service(obj.content_object)
        if obj.content_type.model == "project":
            yield from project(obj.content_object)
        # If we have a new rule, it won't have a name
        if obj.pk:
            yield obj.get_absolute_url(), obj.name

    def sender(obj):
        if obj.content_type.model == "service":
            yield from service(obj.content_object)
        if obj.content_type.model == "project":
            yield from project(obj.content_object)

    def farm(obj):
        yield reverse("farm-list"), _("Farms")
        yield obj.get_absolute_url(), obj.name

    def group(obj):
        yield reverse("group-list"), _("Groups")
        yield reverse("group-detail", kwargs={"pk": obj.pk}), obj.name

    def generator():
        yield reverse("home"), _("Home")
        if isinstance(instance, models.Sender):
            yield from sender(instance)
        if isinstance(instance, models.Project):
            yield from project(instance)
        if isinstance(instance, models.Service):
            yield from service(instance)
        if isinstance(instance, models.Shard):
            yield from shard(instance)
        if isinstance(instance, models.Rule):
            yield from rule(instance)
        if isinstance(instance, models.Alert):
            yield from alert(instance)
        if isinstance(instance, models.Farm):
            yield from farm(instance)
        if isinstance(instance, models.Group):
            yield from group(instance)

    def to_tag():
        yield '<ol class="breadcrumb" v-pre>'
        for href, text in generator():
            yield format_html('<li><a href="{}">{}</a></li>', mark_safe(href), text)
        if label:
            yield format_html('<li class="active">{}</li>', _(label))
        yield "</ol>"

    return mark_safe("".join(to_tag()))


@register.simple_tag(takes_context=True)
def qs_replace(context, k, v):
    """
    Query string handler for paginators

    Assuming we have a query string like ?page=1&search=foo, there are several cases
    in which we want to replace only the page key, while leaving the rest alone.
    This tag allows us to replace individual values (like the current page) while
    carrying over other values (like a search string)

    Example:
    {% qs_replace 'page' page_obj.next_page_number %}
    """
    dict_ = context["request"].GET.copy()
    if v:
        dict_[k] = v
    else:
        dict_.pop(k, None)
    return dict_.urlencode()


@register.simple_tag
def urlqs(view, **kwargs):
    """
    Query string aware version of url template

    Instead of using {% url 'view' %}
    Use {% urlqs 'view' param=value %}

    This is useful for linking to pages that use filters.
    This only works for views that do not need additional parameters
    """
    return reverse(view) + "?" + urlencode(kwargs)


@register.filter()
def get_users_roles(object):
    users_with_perms = get_users_with_perms(
        object,
        attach_perms=True,
        with_superusers=False,
        with_group_users=False,
        # Only include users with Admin, Editor, Viewer permissions
        only_with_perms_in=[
            "service_admin",
            "service_editor",
            "service_viewer",
            "project_admin",
            "project_editor",
            "project_viewer",
            "farm_admin",
            "farm_editor",
            "farm_viewer",
            "group_admin",
            "group_member",
        ],
    ).items()
    return {
        user: [Permission.objects.get(codename=perm).name for perm in perms]
        for user, perms in sorted(users_with_perms, key=lambda item: item[0].username)
    }.items()


@register.filter()
def get_groups_roles(object):
    groups_with_perms = get_groups_with_perms(
        object,
        attach_perms=True,
    ).items()
    return {
        group: [Permission.objects.get(codename=perm).name for perm in perms]
        for group, perms in sorted(groups_with_perms, key=lambda item: item[0].name)
    }.items()
