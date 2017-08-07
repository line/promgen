# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import json
import os
import yaml
from django.test import TestCase


class PromgenTest(TestCase):
    @classmethod
    def data_json(cls, *args):
        with open(os.path.join(os.path.dirname(__file__), *args)) as fp:
            return json.load(fp)

    @classmethod
    def data_yaml(cls, *args):
        with open(os.path.join(os.path.dirname(__file__), *args)) as fp:
            return yaml.load(fp)

    @classmethod
    def data(cls, *args):
        with open(os.path.join(os.path.dirname(__file__), *args)) as fp:
            return fp.read()
