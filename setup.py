from setuptools import find_packages, setup

from promgen.version import __version__

setup(
    name='Promgen',
    author='Paul Traylor',
    packages=find_packages(exclude=['test']),
    version=__version__,
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
        'pyyaml',
        'requests',
    ],
    extras_require={
        'dev': [
            'django-nose',
            'nose-cov',
        ]
    },
    entry_points={
        'console_scripts': [
            'promgen = promgen.manage:main',
        ],
        'promgen.server': [
            'default = promgen.remote',
        ],
        'promgen.sender': [
            'ikasan = promgen.sender.ikasan:SenderIkasan',
            'email = promgen.sender.email:SenderEmail',
            'linenotify = promgen.sender.linenotify:SenderLineNotify',
            'webhook = promgen.sender.webhook:SenderWebhook',
        ],
    }
)
