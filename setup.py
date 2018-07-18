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
    name='promgen',
    author='LINE Corporation',
    author_email='dl_oss_dev@linecorp.com',
    url='https://github.com/line/promgen',
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
        'celery[redis]==4.1.1',
        'dj-database-url',
        'Django >= 2.0, < 2.1',
        'envdir',
        'prometheus-client',
        'python-dateutil',
        'pyyaml',
        'raven',
        'requests',
        'social-auth-app-django >= 2.0.0',
    ],
    include_package_data=True,
    extras_require={
        'dev': [
            'codecov',
            'django-nose',
            'factory_boy',
            'nose-cov',
        ],
        'docs': [
            'Sphinx',
            'sphinxcontrib-httpdomain',
        ],
        'mysql': ['mysqlclient'],
    },
    entry_points={
        'console_scripts': [
            'promgen = promgen.manage:main',
        ],
        'promgen.discovery': [
            'promgen = promgen.discovery.default:DiscoveryPromgen',
        ],
        'promgen.notification': [
            'email = promgen.notification.email:NotificationEmail',
            'ikasan = promgen.notification.ikasan:NotificationIkasan',
            'linenotify = promgen.notification.linenotify:NotificationLineNotify',
            'slack = promgen.notification.slack:NotificationSlack',
            'user = promgen.notification.user:NotificationUser',
            'webhook = promgen.notification.webhook:NotificationWebhook',
        ],
    }
)
