# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import os
import envdir
import pathlib

# Django environment defaults
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "promgen.settings")
default_app_config = "promgen.apps.PromgenConfig"

# Promgen environment defaults
PROMGEN_CONFIG_DIR = os.environ.setdefault(
    "PROMGEN_CONFIG_DIR", os.path.expanduser("~/.config/promgen")
)
PROMGEN_CONFIG_FILE = pathlib.Path(
    os.environ.get("PROMGEN_CONFIG", os.path.join(PROMGEN_CONFIG_DIR, "promgen.yml"))
)
if os.path.exists(PROMGEN_CONFIG_DIR):
    envdir.open(PROMGEN_CONFIG_DIR)
