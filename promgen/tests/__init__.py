# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import json
import os
import yaml


with open(os.path.join(os.path.dirname(__file__), 'examples', 'alertmanager.json')) as fp:
    TEST_ALERT = json.load(fp)

with open(os.path.join(os.path.dirname(__file__), 'examples', 'import.json')) as fp:
    TEST_IMPORT = json.load(fp)

with open(os.path.join(os.path.dirname(__file__), 'examples', 'replace.json')) as fp:
    TEST_REPLACE = json.load(fp)

with open(os.path.join(os.path.dirname(__file__), 'examples', 'settings.yaml')) as fp:
    TEST_SETTINGS = yaml.load(fp)

with open(os.path.join(os.path.dirname(__file__), 'examples', 'import.rule')) as fp:
    TEST_RULE = fp.read()
