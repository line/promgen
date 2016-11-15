from setuptools import find_packages, setup

setup(
    name='Promgen',
    author='Paul Traylor',
    packages=find_packages(exclude=['test']),
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
            'ikasan = promgen.sender.ikasan',
            'email = promgen.sender.email',
            'linenotify = promgen.sender.linenotify',
            'webhook = promgen.sender.webhook',
        ],
    }
)
