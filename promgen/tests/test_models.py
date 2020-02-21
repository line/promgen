# Copyright (c) 2020 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE


from unittest import mock

from django.core.exceptions import ValidationError

from promgen import models
from promgen.tests import PromgenTest


class ModelTest(PromgenTest):
    @mock.patch("django.dispatch.dispatcher.Signal.send")
    def setUp(self, mock_signal):
        self.user = self.add_force_login(id=999, username="Foo")

    def test_names(self):
        # Unicode is ok
        models.Service(name=r"日本語", owner=self.user).full_clean()
        # Spaces are ok
        models.Service(name=r"foo bar", owner=self.user).full_clean()
        # dash or under score are ok
        models.Service(name=r"foo-bar_baz", owner=self.user).full_clean()
        with self.assertRaises(ValidationError):
            # Fail a name with \
            models.Service(name=r"foo/bar", owner=self.user).full_clean()
            models.Service(name=r"foo\bar", owner=self.user).full_clean()
