# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import os
import pathlib

# Django environment defaults
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "promgen.settings")
default_app_config = "promgen.apps.PromgenConfig"

# Promgen environment defaults
PROMGEN_CONFIG_DIR = pathlib.Path(
    os.environ.setdefault("PROMGEN_CONFIG_DIR", os.path.expanduser("~/.config/promgen"))
)

PROMGEN_CONFIG_FILE = pathlib.Path(
    os.environ.get("PROMGEN_CONFIG", str(PROMGEN_CONFIG_DIR / "promgen.yml"))
)

# In the future we want to remove the dependency on envdir, but this will
# require some cleanup and documentation changes, so for now we will just
# ensure that it can't fail here if envdir is not already installed
if PROMGEN_CONFIG_DIR.exists():
    try:
        import envdir
    except ImportError:
        pass
    else:
        envdir.open(PROMGEN_CONFIG_DIR)


if "SECRET_KEY" not in os.environ:
    try:
        from django.utils.crypto import get_random_string
        import warnings

        warnings.warn("Unset SECRET_KEY setting to random for now")
        os.environ["SECRET_KEY"] = get_random_string(
            50, "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
        )
    except ImportError:
        pass

