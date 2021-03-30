# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE

import pathlib
from setuptools import find_packages, setup

# Read version information
# Taken from https://github.com/kennethreitz/pipenv/blob/master/setup.py
about = {}
here = pathlib.Path(__file__).parent / "promgen" / "version.py"
with here.open() as fp:
    exec(fp.read(), about)

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
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Internet :: WWW/HTTP',
    ],
    install_requires=[
        'atomicwrites==1.3.0',
        'celery==4.3.0',
        'django-environ',
        'django-filter',
        'Django==2.2.18',
        'djangorestframework==3.11.2',
        'envdir',
        'kombu==4.6.3',  # https://github.com/celery/kombu/issues/1063
        'prometheus-client==0.7.0',
        'python-dateutil==2.8.0',
        'pyyaml==5.4',
        'requests==2.22.0',
        'sentry_sdk',
        'social-auth-app-django >= 2.0.0',
    ],
    include_package_data=True,
    extras_require={
        'dev': [
            'black',
            'codecov',
            'django-nose',
            'flake8',
            'nose-cov',
            'unittest-xml-reporting',
        ],
        'docs': [
            'Sphinx',
            'sphinxcontrib-httpdomain',
        ],
        'mysql': ['mysqlclient==1.4.2'],
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
