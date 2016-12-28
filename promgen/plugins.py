import logging

from pkg_resources import working_set

logger = logging.getLogger(__name__)


def remotes():
    return working_set.iter_entry_points('promgen.server')


def senders():
    return working_set.iter_entry_points('promgen.sender')

apps = [entry.module_name for entry in working_set.iter_entry_points('promgen.apps')]
