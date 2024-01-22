import django_filters


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
