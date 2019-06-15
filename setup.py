#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'Click',
    'nbgrader',
    'requests',
]

setup_requirements = ['pytest-runner', ]

test_requirements = ['pytest', ]

setup(
    author="Hugo Castilho",
    author_email='hcastilho@lisbondatascience.org',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="Application to grade LDSA notebooks",
    entry_points={
        'console_scripts': [
            'ldsagrader=ldsagrader.ldsagrader:main',
        ],
    },
    install_requires=requirements,
    license="MIT license",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='ldsagrader',
    name='ldsagrader',
    packages=find_packages(include=['ldsagrader']),
    # setup_requires=setup_requirements,
    # test_suite='tests',
    # tests_require=test_requirements,
    url='https://github.com/hcastilho/ldsagrader',
    version='0.1.5',
    zip_safe=False,
)
