import json
import os
import yaml


with open(os.path.join(os.path.dirname(__file__), 'examples', 'alertmanager.json')) as fp:
    TEST_ALERT = json.load(fp)

with open(os.path.join(os.path.dirname(__file__), 'examples', 'import.json')) as fp:
    TEST_IMPORT = json.load(fp)

with open(os.path.join(os.path.dirname(__file__), 'examples', 'replace.json')) as fp:
    TEST_REPLACE = json.load(fp)

with open(os.path.join(os.path.dirname(__file__), 'examples', 'promgen.yml')) as fp:
    TEST_SETTINGS = yaml.load(fp)

with open(os.path.join(os.path.dirname(__file__), 'examples', 'import.rule')) as fp:
    TEST_RULE = fp.read()
