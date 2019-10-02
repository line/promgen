# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import json
import os

import yaml

from django.contrib.auth.models import Permission, User
from django.test import TestCase


class PromgenTest(TestCase):
    @classmethod
    def data_json(cls, *args):
        with open(os.path.join(os.path.dirname(__file__), *args)) as fp:
            return json.load(fp)

    @classmethod
    def data_yaml(cls, *args):
        with open(os.path.join(os.path.dirname(__file__), *args)) as fp:
            return yaml.safe_load(fp)

    @classmethod
    def data(cls, *args):
        with open(os.path.join(os.path.dirname(__file__), *args)) as fp:
            return fp.read()

    def assertRoute(self, response, view, status=200, msg=None):
        self.assertEqual(response.status_code, status, msg)
        self.assertEqual(response.resolver_match.func.__name__, view.as_view().__name__)

    def assertCount(self, model, count, msg=None):
        self.assertEqual(model.objects.count(), count, msg)

    def add_force_login(self, **kwargs):
        user = User.objects.create_user(**kwargs)
        self.client.force_login(user, "django.contrib.auth.backends.ModelBackend")
        return user

    def add_user_permissions(self, *args, user=None):
        codenames = [p.split(".")[1] for p in args]
        permissions = Permission.objects.filter(
            codename__in=codenames, content_type__app_label="promgen"
        )

        if user is None:
            user = self.user

        user.user_permissions.add(*[p for p in permissions])
