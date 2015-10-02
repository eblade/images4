#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#from distutils.core import setup
from setuptools import setup
try:
    from setuptools_behave import behave_test
except ImportError:
    print("Tests require behave, which you don't have.")

name_ = 'images'
version_ = '5.0.0'
packages_ = [
    'images',
    'images.ingest',
    'images.outgest',
    'exifread',
    'exifread.tags',
    'exifread.tags.makernote',
]

classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: POSIX",
    "Operating System :: POSIX :: Linux",
    "Programming Language :: Python :: 3",
]

setup(
    name=name_,
    version=version_,
    author='Johan Egneblad',
    author_email='johan@DELETEMEegneblad.se',
    description='Image library and viewer',
    license="MIT",
    url='https://github.com/eblade/'+name_,
    download_url=('https://github.com/eblade/%s/archive/v%s.tar.gz'
                  % (name_, version_)),
    packages=packages_,
    install_requires=[
        "pillow>=2.5.1",
        "bottle>0.12.7",
        "sqlalchemy>=1.0.0",
    ],
    tests_require=[
        "behave>=1.2.4",
        "pyhamcrest",
    ],
    test_suite='features',
    cmdclass = {
        "test": behave_test,
    },
    scripts=['bin/images', 'bin/setup_images'],
    classifiers = classifiers
)
