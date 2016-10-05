from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import ListView

from promgen import models


class ServiceList(ListView):
    model = models.Service
