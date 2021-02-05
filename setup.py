# -*- coding: utf-8 -*-

"""The setup script."""

import sys
from setuptools import setup, find_packages

requirements = ["connio>=0.1"]

with open("README.md") as f:
    description = f.read()

setup(
    name="xia-pfcu",
    author="Tiago Coutinho",
    author_email="tcoutinho@cells.es",
    version="1.5.0",
    description="xia-pfcu library",
    long_description=description,
    long_description_content_type="text/markdown",
    entry_points={
        "console_scripts": [
            "PFCU = xia_pfcu.tango.server:main [tango]",
        ]
    },
    install_requires=requirements,
    extras_require={
        "tango": ["pytango>=9"],
        "simulator": ["sinstruments>=1"]
    },
    classifiers=[
        "Natural Language :: English",
        "Intended Audience :: Developers",
        "Development Status :: 2 - Pre-Alpha",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)'
    ],
    license="LGPLv3+",
    include_package_data=True,
    keywords="XIA, PFCU, library, tango",
    packages=find_packages(),
    url="https://github.com/tiagocoutinho/xia-pfcu",
    project_urls={
        "Documentation": "https://github.com/tiagocoutinho/xia-pfcu",
        "Source": "https://github.com/tiagocoutinho/xia-pfcu"
    }
)
