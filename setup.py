#!/usr/bin/env python

import os
from pathlib import Path
from typing import Mapping

from setuptools import find_packages
from setuptools import setup

with open("README.md") as readme_file:
    readme = readme_file.read()


with open("requirements.txt") as requiremets_file:
    requirements = requiremets_file.read().split()


def make_extra_requirements() -> Mapping[str, str]:
    extra_requirements = {}
    for req_file_path in Path(__file__).parent.glob("requirements-*.txt"):
        if req_file_path.name not in ["requirements-dev.txt", "requirements-test.txt"]:
            extra_req_name = req_file_path.name[len("requirements-") : -len(".txt")]
            with req_file_path.open() as extra_req_file:
                extra_requirements = {
                    **extra_requirements,
                    extra_req_name: extra_req_file.read().split(),
                }

    return extra_requirements


version = os.environ["PKG_VERSION"]

setup(
    author="Dimitrios Dedoussis",
    author_email="dimitrios@dedouss.is",
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Framework :: Flask",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    description="SocketIO framework driven by the AsyncAPI specification. Built on top of Flask-SocketIO. Inspired by Connexion.",
    install_requires=requirements,
    extras_require=make_extra_requirements(),
    license="MIT license",
    long_description=readme,
    long_description_content_type="text/markdown",
    include_package_data=True,
    package_data={
        "asynction": ["py.typed"],
    },
    keywords=" ".join(
        [
            "asyncapi",
            "websockets",
            "socketio",
            "socket.io",
            "api",
            "oauth",
            "flask",
            "microservice",
            "framework",
            "specification",
            "flask-socketio",
            "connexion",
            "mock",
        ]
    ),
    name="asynction",
    packages=find_packages(include=["asynction", "asynction.*"]),
    url="https://github.com/dedoussis/asynction",
    version=version,
    zip_safe=False,
)
