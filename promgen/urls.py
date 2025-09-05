# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

"""promgen URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt
from rest_framework import routers

from promgen import proxy, rest, views

router = routers.DefaultRouter()
router.register("all", rest.AllViewSet, basename="all")
router.register("service", rest.ServiceViewSet)
router.register("shard", rest.ShardViewSet)
router.register("project", rest.ProjectViewSet)
router.register("farm", rest.FarmViewSet)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.HomeList.as_view(), name="home"),
    # Data source
    path("datasource", views.DatasourceList.as_view(), name="datasource-list"),
    path("datasource/<int:pk>", views.DatasourceDetail.as_view(), name="datasource-detail"),
    # Services
    path("new/service", views.ServiceRegister.as_view(), name="service-new"),
    path("service", views.ServiceList.as_view(), name="service-list"),
    path("service/<int:pk>", views.ServiceDetail.as_view(), name="service-detail"),
    path("service/<int:pk>/delete", views.ServiceDelete.as_view(), name="service-delete"),
    path("service/<int:pk>/new", views.ProjectRegister.as_view(), name="project-new"),
    path("service/<int:pk>/update", views.ServiceUpdate.as_view(), name="service-update"),
    path("service/<int:pk>/notifier", views.ServiceNotifierRegister.as_view(), name="service-notifier"),
    # Projects
    path("project/<int:pk>", views.ProjectDetail.as_view(), name="project-detail"),
    path("project/<int:pk>/delete", views.ProjectDelete.as_view(), name="project-delete"),
    path("project/<int:pk>/update", views.ProjectUpdate.as_view(), name="project-update"),
    path("project/<int:pk>/unlink", views.UnlinkFarm.as_view(), name="farm-unlink"),
    path("project/<int:pk>/link/<source>", views.FarmLink.as_view(), name="farm-link"),
    path("project/<int:pk>/newfarm", views.FarmRegister.as_view(), name="farm-new"),
    path("project/<int:pk>/exporter", views.ExporterRegister.as_view(), name="project-exporter"),
    path("project/<int:pk>/notifier", views.ProjectNotifierRegister.as_view(), name="project-notifier"),
    path("project/<int:pk>/scrape", views.ExporterScrape.as_view(), name="exporter-scrape"),
    # Exporters
    path("exporter/<int:pk>/delete", views.ExporterDelete.as_view(), name="exporter-delete"),
    path("exporter/<int:pk>/toggle", views.ExporterToggle.as_view(), name="exporter-toggle"),
    # URLs
    path("url", views.URLList.as_view(), name="url-list"),
    path("url/<int:pk>/new", views.URLRegister.as_view(), name="url-new"),
    path("url/<int:pk>/delete", views.URLDelete.as_view(), name="url-delete"),
    # Farms
    path("farm", views.FarmList.as_view(), name="farm-list"),
    path("farm/<int:pk>", views.FarmDetail.as_view(), name="farm-detail"),
    path("farm/<int:pk>/refresh", views.FarmRefresh.as_view(), name="farm-refresh"),
    path("farm/<int:pk>/hosts", views.HostRegister.as_view(), name="hosts-add"),
    path("farm/<int:pk>/update", views.FarmUpdate.as_view(), name="farm-update"),
    path("farm/<int:pk>/delete", views.FarmDelete.as_view(), name="farm-delete"),
    path("farm/<int:pk>/convert", views.FarmConvert.as_view(), name="farm-convert"),
    # Hosts
    path("host/", views.HostList.as_view(), name="host-list"),
    path("host/<slug>", views.HostDetail.as_view(), name="host-detail"),
    path("host/<int:pk>/delete", views.HostDelete.as_view(), name="host-delete"),
    # Notifiers
    path("notifier/<int:pk>/delete", views.NotifierDelete.as_view(), name="notifier-delete"),
    path("notifier/<int:pk>/test", views.NotifierTest.as_view(), name="notifier-test"),
    path("notifier/<int:pk>", views.NotifierUpdate.as_view(), name="notifier-edit"),
    path("notifier/<int:pk>/toggle", views.NotifierToggle.as_view(), name="notifier-toggle"),
    # Rules
    path("rule", views.RulesList.as_view(), name="rules-list"),
    path("rule/<int:pk>", views.RuleDetail.as_view(), name="rule-detail"),
    path("rule/<int:pk>/edit", views.RuleUpdate.as_view(), name="rule-edit"),
    path("rule/<int:pk>/delete", views.RuleDelete.as_view(), name="rule-delete"),
    path("rule/<int:pk>/toggle", views.RuleToggle.as_view(), name="rule-toggle"),
    path("rule/<int:pk>/test", csrf_exempt(views.RuleTest.as_view()), name="rule-test"),
    path("rule/<int:pk>/duplicate", views.RulesCopy.as_view(), name="rule-overwrite"),
    # Permissions
    path("permission/assign", views.PermissionAssign.as_view(), name="permission-assign"),
    path("permission/delete", views.PermissionDelete.as_view(), name="permission-delete"),
    # Groups
    path("group", views.GroupList.as_view(), name="group-list"),
    path("group/new", views.GroupRegister.as_view(), name="group-register"),
    path("group/<int:pk>", views.GroupDetail.as_view(), name="group-detail"),
    path("group/<int:pk>/add-member", views.GroupAddMember.as_view(), name="group-add-member"),
    path("group/<int:pk>/update-member", views.GroupUpdateMember.as_view(), name="group-update-member"),
    path("group/<int:pk>/remove-member", views.GroupRemoveMember.as_view(), name="group-remove-member"),
    path("group/<int:pk>/update", views.GroupUpdate.as_view(), name="group-update"),
    path("group/<int:pk>/delete", views.GroupDelete.as_view(), name="group-delete"),
    # Generic Rules
    path("<content_type>/<object_id>/rule", views.AlertRuleRegister.as_view(), name="rule-new"),
    # Other miscellaneous
    path("audit", views.AuditList.as_view(), name="audit-list"),
    path("site", views.SiteDetail.as_view(), name="site-detail"),
    path("profile", views.Profile.as_view(), name="profile"),
    path("profile/token/generate", views.ProfileTokenGenerate.as_view(), name="token-generate"),
    path("profile/token/delete", views.ProfileTokenDelete.as_view(), name="token-delete"),
    path("import", views.Import.as_view(), name="import"),
    path("import/rules", views.RuleImport.as_view(), name="rule-import"),
    path("search", views.Search.as_view(), name="search"),
    path("metrics", csrf_exempt(views.Metrics.as_view()), name="metrics"),
    # Alerts
    path("alert", views.AlertList.as_view(), name="alert-list"),
    path("alert/<int:pk>", views.AlertDetail.as_view(), name="alert-detail"),
    # Third Party / Auth
    path("", include("django.contrib.auth.urls")),
    path("", include("social_django.urls", namespace="social")),
    # Legacy API
    path("api/v1/config", csrf_exempt(views.ApiConfig.as_view())),
    path("api/", include((router.urls, "api"), namespace="old-api")),
    path("api/v1/rules", csrf_exempt(views.RulesConfig.as_view())),
    path("api/v1/targets", csrf_exempt(views.ApiConfig.as_view()), name="config-targets"),
    path("api/v1/urls", csrf_exempt(views.URLConfig.as_view()), name="config-urls"),
    path("api/v1/alerts", csrf_exempt(rest.AlertReceiver.as_view()), name="alert"),
    path("api/v1/host/<slug>", views.HostDetail.as_view()),
    # Prometheus Proxy
    # these apis need to match the same path because Promgen can pretend to be a Prometheus API
    path("graph", proxy.ProxyGraph.as_view()),
    path("api/v1/labels", proxy.ProxyLabels.as_view(), name="proxy-label"),
    path("api/v1/label/<label>/values", proxy.ProxyLabelValues.as_view(), name="proxy-values"),
    path("api/v1/query_range", proxy.ProxyQueryRange.as_view()),
    path("api/v1/query", proxy.ProxyQuery.as_view(), name="proxy-query"),
    path("api/v1/series", proxy.ProxySeries.as_view()),
    # Alertmanager Proxy
    # Promgen does not pretend to be an Alertmanager so these can be slightly different
    path("proxy/v1/alerts", csrf_exempt(proxy.ProxyAlerts.as_view()), name="proxy-alerts"),
    path("proxy/v1/silences", csrf_exempt(proxy.ProxySilences.as_view()), name="proxy-silence"),
    path("proxy/v1/silences/<silence_id>", csrf_exempt(proxy.ProxyDeleteSilence.as_view()), name="proxy-silence-delete"),
    path("proxy/v2/silences", csrf_exempt(proxy.ProxySilencesV2.as_view()), name="proxy-silence-v2"),
    # Promgen rest API
    path("rest/", include((router.urls, "api"), namespace="api")),
]

try:
    import debug_toolbar

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]
except ImportError:
    pass
