import django_filters
from django.contrib.contenttypes.models import ContentType

from promgen import models


class ShardFilter(django_filters.rest_framework.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr="contains")


class ServiceFilter(django_filters.rest_framework.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr="contains")


class ProjectFilter(django_filters.rest_framework.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr="contains")
    service = django_filters.CharFilter(field_name="service__name", lookup_expr="contains")
    shard = django_filters.CharFilter(field_name="shard__name", lookup_expr="contains")


class RuleFilter(django_filters.rest_framework.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr="contains")
    parent = django_filters.CharFilter(field_name="parent__name", lookup_expr="contains")
    enabled = django_filters.BooleanFilter(field_name="enabled")


class FarmFilter(django_filters.rest_framework.FilterSet):
    name = django_filters.CharFilter(
        field_name="name",
        lookup_expr="contains",
        help_text="Filter by farm name containing a specific substring. Example: name=Example Farm",
    )
    source = django_filters.ChoiceFilter(
        field_name="source",
        choices=[(name, name) for name, _ in models.Farm.driver_set()],
        lookup_expr="exact",
        help_text="Filter by exact source name. Example: source=promgen",
    )


class UserFilter(django_filters.rest_framework.FilterSet):
    username = django_filters.CharFilter(
        field_name="username",
        lookup_expr="contains",
        help_text="Filter by username containing a specific substring. Example: username=Example Username",
    )
    email = django_filters.CharFilter(
        field_name="email",
        lookup_expr="contains",
        help_text="Filter by email containing a specific substring. Example: email=example@example.com",
    )


def filter_content_type(queryset, name, value):
    try:
        content_type_id = ContentType.objects.get(model=value, app_label="promgen").id
        return queryset.filter(content_type_id=content_type_id)
    except ContentType.DoesNotExist:
        return queryset.none()


class AuditFilter(django_filters.rest_framework.FilterSet):
    object_id = django_filters.NumberFilter(
        field_name="object_id",
        lookup_expr="exact",
        help_text="Filter by exact object ID. Example: object_id=123",
    )
    content_type = django_filters.ChoiceFilter(
        field_name="content_type",
        choices=[
            ("service", "Service"),
            ("project", "Project"),
            ("rule", "Rule"),
            ("sender", "Notifier"),
            ("exporter", "Exporter"),
            ("url", "URL"),
            ("farm", "Farm"),
            ("host", "Host"),
        ],
        method=filter_content_type,
        help_text="Filter by content type model name. Example: content_type=service",
    )
    user = django_filters.CharFilter(
        field_name="user__username",
        lookup_expr="exact",
        help_text="Filter by exact owner username. Example: owner=Example Owner",
    )


class NotifierFilter(django_filters.rest_framework.FilterSet):
    sender = django_filters.ChoiceFilter(
        field_name="sender",
        choices=[(module_name, module_name) for module_name, _ in models.Sender.driver_set()],
        help_text="Filter by sender type. Example: sender=promgen.notification.email",
    )
    value = django_filters.CharFilter(
        field_name="value",
        lookup_expr="contains",
        help_text="Filter by value containing a specific substring. Example: value=demo@example.com",
    )
    object_id = django_filters.NumberFilter(
        field_name="object_id",
        lookup_expr="exact",
        help_text="Filter by exact object ID. Example: object_id=123",
    )
    content_type = django_filters.ChoiceFilter(
        field_name="content_type",
        choices=[
            ("service", "Service"),
            ("project", "Project"),
        ],
        method=filter_content_type,
        help_text="Filter by content type model name. Example: content_type=service",
    )
    owner = django_filters.CharFilter(
        field_name="owner__username",
        lookup_expr="exact",
        help_text="Filter by exact owner username. Example: owner=Example Owner",
    )


class RuleFilterV2(django_filters.rest_framework.FilterSet):
    name = django_filters.CharFilter(
        field_name="name",
        lookup_expr="contains",
        help_text="Filter by rule name containing a specific substring. Example: name=Example Rule",
    )
    parent = django_filters.CharFilter(
        field_name="parent__name",
        lookup_expr="contains",
        help_text="Filter by parent rule name containing a specific substring. Example: parent=Example Parent",
    )
    enabled = django_filters.BooleanFilter(
        field_name="enabled",
        help_text="Filter by enabled status (true or false). Example: enabled=true",
    )
    object_id = django_filters.NumberFilter(
        field_name="object_id",
        lookup_expr="exact",
        help_text="Filter by exact object ID. Example: object_id=123",
    )
    content_type = django_filters.ChoiceFilter(
        field_name="content_type",
        choices=[
            ("service", "Service"),
            ("project", "Project"),
            ("site", "Site"),
        ],
        method=filter_content_type,
        help_text="Filter by content type model name. Example: content_type=service",
    )


class ExporterFilter(django_filters.rest_framework.FilterSet):
    project = django_filters.CharFilter(
        field_name="project__name",
        lookup_expr="contains",
        help_text="Filter by project name containing a specific substring. Example: project=Example Project",
    )
    job = django_filters.CharFilter(
        field_name="job",
        lookup_expr="contains",
        help_text="Filter by job name containing a specific substring. Example: job=prometheus",
    )
    path = django_filters.CharFilter(
        field_name="path",
        lookup_expr="contains",
        help_text="Filter by path containing a specific substring. Example: path=/metrics",
    )
    scheme = django_filters.ChoiceFilter(
        field_name="scheme",
        choices=[
            ("http", "HTTP"),
            ("https", "HTTPS"),
        ],
        lookup_expr="exact",
        help_text="Filter by exact scheme. Example: scheme=http",
    )
    enabled = django_filters.BooleanFilter(
        field_name="enabled",
        help_text="Filter by enabled status (true or false). Example: enabled=true",
    )


class URLFilter(django_filters.rest_framework.FilterSet):
    project = django_filters.CharFilter(
        field_name="project__name",
        lookup_expr="contains",
        help_text="Filter by project name containing a specific substring. Example: project=Example Project",
    )
    probe = django_filters.ChoiceFilter(
        field_name="probe__module",
        choices=models.Probe.objects.values_list("module", "description").distinct(),
        help_text="Filter by exact probe scheme. Example: probe=http_2xx",
    )


class ProjectFilterV2(django_filters.rest_framework.FilterSet):
    name = django_filters.CharFilter(
        field_name="name",
        lookup_expr="contains",
        help_text="Filter by project name containing a specific substring. Example: name=Example Project",
    )
    service = django_filters.CharFilter(
        field_name="service__name",
        lookup_expr="exact",
        help_text="Filter by exact service name. Example: service=Example Service",
    )
    shard = django_filters.CharFilter(
        field_name="shard__name",
        lookup_expr="exact",
        help_text="Filter by exact shard name. Example: shard=Example Shard",
    )
    owner = django_filters.CharFilter(
        field_name="owner__username",
        lookup_expr="exact",
        help_text="Filter by exact owner username. Example: owner=Example Owner",
    )


class ServiceFilterV2(django_filters.rest_framework.FilterSet):
    name = django_filters.CharFilter(
        field_name="name",
        lookup_expr="contains",
        help_text="Filter by service name containing a specific substring. Example: name=Example Service",
    )
    owner = django_filters.CharFilter(
        field_name="owner__username",
        lookup_expr="exact",
        help_text="Filter by exact owner username. Example: owner=Example Owner",
    )
