"""promgen URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.views.decorators.csrf import csrf_exempt

from promgen import views

urlpatterns = [
    url(r'^admin/', admin.site.urls),

    url(r'^$', views.ShardList.as_view(), name='home'),
    url(r'^shard/(?P<pk>[0-9]+)/$', views.ShardDetail.as_view(), name='shard-detail'),
    url(r'^shard/(?P<pk>[0-9]+)/new$', views.ServiceRegister.as_view(), name='service-new'),

    url(r'^service/$', views.ServiceList.as_view(), name='service-list'),
    url(r'^service/(?P<pk>[0-9]+)/$', views.ServiceDetail.as_view(), name='service-detail'),
    url(r'^service/(?P<pk>[0-9]+)/delete$', views.ServiceDelete.as_view(), name='service-delete'),
    url(r'^service/(?P<pk>[0-9]+)/rules/new$', views.RuleRegister.as_view(), name='rule-new'),
    url(r'^service/(?P<pk>[0-9]+)/rules/copy$', views.RulesCopy.as_view(), name='rule-copy'),
    url(r'^service/(?P<pk>[0-9]+)/new$', views.ProjectRegister.as_view(), name='project-new'),
    url(r'^service/(?P<pk>[0-9]+)/targets$', views.ServiceTargets.as_view(), name='service-targets'),
    url(r'^service/(?P<pk>[0-9]+)/rules$', views.ServiceRules.as_view(), name='service-rules'),
    url(r'^service/(?P<pk>[0-9]+)/update$', views.ServiceUpdate.as_view(), name='service-update'),
    url(r'^service/(?P<pk>[0-9]+)/sender$', views.ServiceSenderRegister.as_view(), name='service-sender'),

    url(r'^project/(?P<pk>[0-9]+)/$', views.ProjectDetail.as_view(), name='project-detail'),
    url(r'^project/(?P<pk>[0-9]+)/delete$', views.ProjectDelete.as_view(), name='project-delete'),
    url(r'^project/(?P<pk>[0-9]+)/update$', views.ProjectUpdate.as_view(), name='project-update'),
    url(r'^project/(?P<pk>[0-9]+)/unlink$', views.UnlinkFarm.as_view(), name='farm-unlink'),
    url(r'^project/(?P<pk>[0-9]+)/link/(?P<source>\w+)$', views.FarmLink.as_view(), name='farm-link'),
    url(r'^project/(?P<pk>[0-9]+)/newfarm$', views.FarmRegsiter.as_view(), name='farm-new'),
    url(r'^project/(?P<pk>[0-9]+)/exporter$', views.ExporterRegister.as_view(), name='project-exporter'),
    url(r'^project/(?P<pk>[0-9]+)/targets$', views.ProjectTargets.as_view(), name='project-targets'),
    url(r'^project/(?P<pk>[0-9]+)/sender$', views.ProjectSenderRegister.as_view(), name='project-sender'),

    url(r'^exporter/(?P<pk>[0-9]+)/delete$', views.ExporterDelete.as_view(), name='exporter-delete'),

    url(r'^url$', views.URLList.as_view(), name='url-list'),
    url(r'^url/(?P<pk>[0-9]+)/new$', views.URLRegister.as_view(), name='url-new'),
    url(r'^url/(?P<pk>[0-9]+)/delete$', views.URLDelete.as_view(), name='url-delete'),

    url(r'^farm/$', views.FarmList.as_view(), name='farm-list'),
    url(r'^farm/(?P<pk>[0-9]+)$', views.FarmDetail.as_view(), name='farm-detail'),
    url(r'^farm/(?P<pk>[0-9]+)/refresh$', views.FarmRefresh.as_view(), name='farm-refresh'),
    url(r'^farm/(?P<pk>[0-9]+)/hosts$', views.HostRegister.as_view(), name='hosts-add'),
    url(r'^farm/(?P<pk>[0-9]+)/update$', views.FarmUpdate.as_view(), name='farm-update'),
    url(r'^farm/(?P<pk>[0-9]+)/delete$', views.FarmDelete.as_view(), name='farm-delete'),
    url(r'^farm/(?P<pk>[0-9]+)/convert$', views.FarmConvert.as_view(), name='farm-convert'),

    url(r'^host/$', views.HostList.as_view(), name='host-list'),
    url(r'^host/(?P<pk>[0-9]+)/$', views.HostDetail.as_view(), name='host-detail'),
    url(r'^host/(?P<name>\S+)/$', views.HostSearch.as_view(), name='host-search'),
    url(r'^host/(?P<pk>[0-9]+)/delete$', views.HostDelete.as_view(), name='host-delete'),

    url(r'^sender/(?P<pk>[0-9]+)/delete$', views.SenderDelete.as_view(), name='sender-delete'),
    url(r'^sender/(?P<pk>[0-9]+)/test$', views.SenderTest.as_view(), name='sender-test'),

    url(r'^rules/$', views.RulesList.as_view(), name='rules-list'),
    url(r'^rule/(?P<pk>[0-9]+)/edit$', views.RuleUpdate.as_view(), name='rule-edit'),
    url(r'^rule/(?P<pk>[0-9]+)/delete$', views.RuleDelete.as_view(), name='rule-delete'),
    url(r'^rule/(?P<pk>[0-9]+)/toggle$', views.RuleToggle.as_view(), name='rule-toggle'),

    url(r'^api/v1/config', csrf_exempt(views.ApiConfig.as_view()), name='config-targets'),
    url(r'^api/v1/rules', csrf_exempt(views.RulesConfig.as_view()), name='config-rules'),
    url(r'^api/v1/urls', csrf_exempt(views.URLConfig.as_view()), name='config-urls'),

    url(r'^audit/$', views.AuditList.as_view(), name='audit-list'),
    url(r'^status/$', views.Status.as_view(), name='status'),
    url(r'^import/$', views.Import.as_view(), name='import'),

    url(r'^mute$', views.Mute.as_view(), name='mute'),
    url(r'^mute/service/(?P<service>.+)$', views.Mute.as_view(), name='service-mute'),
    url(r'^mute/project/(?P<project>.+)$', views.Mute.as_view(), name='project-mute'),
    url(r'^mute/farm/(?P<farm>.+)$', views.Mute.as_view(), name='farm-mute'),
    url(r'^mute/host/(?P<host>.+)$', views.Mute.as_view(), name='host-mute'),


    url(r'^search/$', views.Search.as_view(), name='search'),
    url(r'^alert$', csrf_exempt(views.Alert.as_view()), name='alert'),
    url(r'^metrics$', csrf_exempt(views.Metrics.as_view()), name='metrics'),
    url(r'^commit$', csrf_exempt(views.Commit.as_view()), name='commit'),

    url(r'^ajax/alert$', csrf_exempt(views.AjaxAlert.as_view()), name='ajax-alert'),
]

if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns += [
            url(r'^__debug__/', include(debug_toolbar.urls)),
        ]
    except:
        pass
