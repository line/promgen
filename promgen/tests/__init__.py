# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import json
from django.urls import reverse
import yaml

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.conf import settings


class Data:
    def __init__(self, *args, test_dir=settings.BASE_DIR / "promgen" / "tests"):
        self.path = test_dir.joinpath(*args)

    def json(self):
        with self.path.open() as fp:
            return json.load(fp)

    def yaml(self):
        with self.path.open() as fp:
            return yaml.safe_load(fp)

    def raw(self):
        with self.path.open() as fp:
            return fp.read()


class PromgenTest(TestCase):
    longMessage = True
    fixtures = ["testcases.yaml"]

    def fireAlert(self, source="alertmanager.json", data=None):
        if data is None:
            data = Data("examples", source).raw()

        return self.client.post(
            reverse("alert"), data=data, content_type="application/json"
        )

    def assertRoute(self, response, view, status=200, msg=None):
        self.assertEqual(response.status_code, status, msg)
        self.assertEqual(response.resolver_match.func.__name__, view.as_view().__name__)

    def assertCount(self, model, count, msg=None):
        self.assertEqual(model.objects.count(), count, msg)

    def force_login(self, username, **kwargs):
        user = User.objects.get(username=username, **kwargs)
        self.client.force_login(user, "django.contrib.auth.backends.ModelBackend")
        return user

    def assertMockCalls(self, mock_func, *args, **kwargs):
        # normally we would want to use mock_func.assert_called_with but
        # the check is too strict when it comes to dictionary arguments. By writing
        # our own wrapper around it, we can check the arguments match without
        # also requering the dictionary to have the same order
        # We split them here, instead of passing to assertEquals, so that we have
        # the arguments directly and not a call() object
        call_args, call_kwargs = mock_func.call_args
        self.assertEquals((call_args, call_kwargs), (args, kwargs))

    def add_user_permissions(self, *args, user=None):
        codenames = [p.split(".")[1] for p in args]
        permissions = Permission.objects.filter(
            codename__in=codenames, content_type__app_label="promgen"
        )

        if user is None:
            user = self.user

        user.user_permissions.add(*[p for p in permissions])


SETTINGS = Data("examples", "promgen.yml").yaml()
