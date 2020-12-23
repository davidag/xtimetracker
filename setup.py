# SPDX-FileCopyrightText: 2015-2019 Tailordev
# SPDX-FileCopyrightText: 2020 The tt Authors
#
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: MIT

"""Setup file for tt distribution."""

from os.path import join

from setuptools import setup


def readme():
    """Return contents of README.rst"""
    return open('README.rst').read()


# read package meta-data from version.py
pkg = {}
mod = join('tt', 'version.py')
exec(compile(open(mod).read(), mod, 'exec'), {}, pkg)


def parse_requirements(requirements, ignore=('setuptools',)):
    """Read dependencies from requirements file (with version numbers if any)

    Note: this implementation does not support requirements files with extra
    requirements
    """
    with open(requirements) as f:
        packages = set()
        for line in f:
            line = line.strip()
            if line.startswith(('#', '-r', '--')):
                continue
            if '#egg=' in line:
                line = line.split('#egg=')[1]
            pkg = line.strip()
            if pkg not in ignore:
                packages.add(pkg)
        return tuple(packages)


setup(
    name='tt',
    version=pkg['version'],
    description='A wonderful CLI to track your time!',
    url="https://gitlab.com/davidalfonso/tt",
    packages=['tt'],
    author='David Alfonso',
    author_email='developer@davidalfonso.es',
    license='GPL-3.0-or-later AND MIT',
    long_description=readme(),
    install_requires=parse_requirements('requirements.txt'),
    python_requires='>=3.6',
    tests_require=parse_requirements('requirements-dev.txt'),
    entry_points={
        'console_scripts': [
            'tt = tt.__main__:cli',
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Customer Service",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Other Audience",
        "License :: OSI Approved :: MIT License",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Environment :: Console",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Office/Business",
        "Topic :: Utilities",
    ],
    keywords='tt time-tracking time tracking monitoring report',
)
