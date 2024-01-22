# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import logging

from pkg_resources import working_set

logger = logging.getLogger(__name__)


def discovery():
    return working_set.iter_entry_points("promgen.discovery")


def notifications():
    return working_set.iter_entry_points("promgen.notification")


# Since plugins may need to load other resources bundled with them, we loop
# through an additional promgen.apps entry point so that the default django
# project loaders work as expected. This also should simplfy some configuration
# for plugin authors
apps_from_setuptools = [
    entry.module_name for entry in working_set.iter_entry_points("promgen.apps")
]
