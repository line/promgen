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

    url(r'^$', views.ServiceList.as_view(), name='service-list'),
    url(r'^service/new$', views.RegisterService.as_view(), name='service-new'),
    url(r'^service/(?P<pk>[0-9]+)/$', views.ServiceDetail.as_view(), name='service-detail'),
    url(r'^service/(?P<pk>[0-9]+)/delete$', views.ServiceDelete.as_view(), name='service-delete'),
    url(r'^service/(?P<pk>[0-9]+)/rules$', views.RulesList.as_view(), name='service-rules'),
    url(r'^service/(?P<pk>[0-9]+)/rules/new$', views.RegisterRule.as_view(), name='rule-new'),
    url(r'^service/(?P<pk>[0-9]+)/new$', views.RegisterProject.as_view(), name='project-new'),

    url(r'^project/(?P<pk>[0-9]+)/$', views.ProjectDetail.as_view(), name='project-detail'),
    url(r'^project/(?P<pk>[0-9]+)/delete$', views.ProjectDelete.as_view(), name='project-delete'),
    url(r'^project/(?P<pk>[0-9]+)/unlink$', views.UnlinkFarm.as_view(), name='farm-unlink'),
    url(r'^project/(?P<pk>[0-9]+)/link/(?P<source>\w+)$', views.FarmLink.as_view(), name='farm-link'),
    url(r'^project/(?P<pk>[0-9]+)/newfarm$', views.FarmNew.as_view(), name='farm-new'),
    url(r'^project/(?P<pk>[0-9]+)/exporter$', views.RegisterExporter.as_view(), name='project-exporter'),

    url(r'^exporter/(?P<pk>[0-9]+)/delete$', views.ExporterDelete.as_view(), name='exporter-delete'),
    url(r'^farm/(?P<pk>[0-9]+)/$', views.FarmRefresh.as_view(), name='farm-refresh'),
    url(r'^rules/$', views.RulesList.as_view(), name='rules-list'),
    url(r'^api/v1/config', views.ApiConfig.as_view()),
    url(r'^host/$', views.HostList.as_view(), name='host-list'),
    url(r'^audit/$', views.AuditList.as_view(), name='audit-list'),

    url(r'^alert$', csrf_exempt(views.Alert.as_view()), name='alert'),
]

if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns += [
            url(r'^__debug__/', include(debug_toolbar.urls)),
        ]
    except:
        pass
