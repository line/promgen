from setuptools import find_packages, setup

setup(
    name='Promgen',
    author='Paul Traylor',
    packages=find_packages(exclude=['test']),
    install_requires=[
        'Django',
        'pyyaml',
        'requests',
    ],
    test_requires=[
        'nose-cov',
        'django-nose'
    ],
    entry_points={
        'console_scripts': [
            'promgen = promgen.manage:main',
        ],
        'promgen.server': [
            'default = promgen.server',
        ],
        'promgen.sender': [
            'ikasan = promgen.sender.ikasan',
            'email = promgen.sender.email',
            'linenotify = promgen.sender.linenotify',
            'webhook = promgen.sender.webhook',
        ],
    }
)
