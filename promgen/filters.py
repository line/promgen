import django_filters
from django.contrib.contenttypes.models import ContentType


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
    name = django_filters.CharFilter(field_name="name", lookup_expr="contains")
    source = django_filters.CharFilter(field_name="source", lookup_expr="exact")


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
