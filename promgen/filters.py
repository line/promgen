import django_filters
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models import F, Value
from django.db.models.functions import Coalesce, NullIf

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
    name = django_filters.CharFilter(field_name="name", lookup_expr="contains")
    source = django_filters.CharFilter(field_name="source", lookup_expr="exact")


def filter_content_type(queryset, name, value):
    try:
        if value == "group":
            content_type_id = ContentType.objects.get(model=value, app_label="auth").id
        elif value == "user":
            content_type_id = ContentType.objects.get_for_model(User).id
        else:
            content_type_id = ContentType.objects.get(model=value, app_label="promgen").id

        field_name = (
            "parent_content_type_id" if name == "parent_content_type" else "content_type_id"
        )
        return queryset.filter(**{field_name: content_type_id})
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
            ("exporter", "Exporter"),
            ("farm", "Farm"),
            ("group", "Group"),
            ("host", "Host"),
            ("project", "Project"),
            ("rule", "Rule"),
            ("sender", "Notifier"),
            ("service", "Service"),
            ("url", "URL"),
        ],
        method=filter_content_type,
        help_text="Filter by content type model name. Example: content_type=service",
    )
    user = django_filters.CharFilter(
        field_name="user__username",
        lookup_expr="exact",
        help_text="Filter by exact owner username. Example: owner=Example Owner",
    )
    parent_object_id = django_filters.NumberFilter(
        field_name="parent_object_id",
        lookup_expr="exact",
        help_text="Filter by exact parent object ID. Example: parent_object_id=123",
    )
    parent_content_type = django_filters.ChoiceFilter(
        field_name="parent_content_type",
        choices=[
            ("group", "Group"),
            ("project", "Project"),
            ("service", "Service"),
        ],
        method=filter_content_type,
        help_text="Filter by parent content type model name. Example: parent_content_type=service",
    )


class NotifierFilter(django_filters.rest_framework.FilterSet):
    sender = django_filters.ChoiceFilter(
        field_name="sender",
        choices=[(module_name, module_name) for module_name, _ in models.Sender.driver_set()],
        help_text="Filter by sender type. Example: sender=promgen.notification.email",
    )
    value = django_filters.CharFilter(
        method="filter_value",
        help_text="Filter by value (or alias if present) containing a specific substring. "
        "Example: value=demo@example.com",
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
            ("user", "User"),
        ],
        method=filter_content_type,
        help_text="Filter by content type model name. Example: content_type=service",
    )
    owner = django_filters.CharFilter(
        field_name="owner__username",
        lookup_expr="exact",
        help_text="Filter by exact owner username. Example: owner=Example Owner",
    )

    def filter_value(self, queryset, name, value):
        # Annotate the queryset with an effective_value that uses alias if it's not empty,
        # otherwise falls back to value. This is equivalent to the SQL expression:
        # WHERE COALESCE(NULLIF(promgen_sender.alias,), promgen_sender.value) LIKE '%value%'
        queryset = queryset.annotate(
            effective_value=Coalesce(NullIf(F("alias"), Value("")), F("value"))
        )
        return queryset.filter(effective_value__contains=value)
