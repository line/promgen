# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import os
from setuptools import find_packages, setup

# Read version information
# Taken from https://github.com/kennethreitz/pipenv/blob/master/setup.py
about = {}
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "promgen", "version.py")) as f:
    exec(f.read(), about)

setup(
    name='Promgen',
    author='LINE Corporation',
    packages=find_packages(exclude=['test']),
    version=about['__version__'],
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Internet :: WWW/HTTP',
    ],
    install_requires=[
        'atomicwrites',
        'celery[redis]==4.0.2',
        'dj_database_url',
        'Django >= 1.10, < 1.11',
        'envdir',
        'prometheus_client',
        'python-dateutil',
        'pyyaml',
        'raven',
        'requests',
        'social-auth-app-django',
    ],
    extras_require={
        'dev': [
            'codecov',
            'django-nose',
            'nose-cov',
        ]
    },
    entry_points={
        'console_scripts': [
            'promgen = promgen.manage:main',
        ],
        'promgen.discovery': [
            'promgen = promgen.discovery.default:DiscoveryPromgen',
        ],
        'promgen.notification': [
            'ikasan = promgen.notification.ikasan:NotificationIkasan',
            'email = promgen.notification.email:NotificationEmail',
            'linenotify = promgen.notification.linenotify:NotificationLineNotify',
            'webhook = promgen.notification.webhook:NotificationWebhook',
        ],
    }
)
