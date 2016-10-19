from setuptools import find_packages, setup

setup(
    name='Promgen',
    author='Paul Traylor',
    packages=find_packages(exclude=['test']),
    install_requires=[
        'Django',
    ],
    entry_points={
        'console_scripts': [
            'promgen = promgen.manage:main',
        ],
    }
)
