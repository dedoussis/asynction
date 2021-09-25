#!/usr/bin/env python

import os
from pathlib import Path
from typing import Mapping
from typing import Sequence

from setuptools import find_packages
from setuptools import setup

with open("README.md") as readme_file:
    readme = readme_file.read()


with open("requirements.txt") as requiremets_file:
    requirements = requiremets_file.read().split()


def parse_requirements(file_path: Path) -> Sequence[str]:
    reqs = []
    with file_path.open() as f:
        raw_reqs = f.read().split(os.linesep)
        for raw_req in raw_reqs:
            if raw_req:
                stripped_raw_req = raw_req.strip()

                expanded_reqs = (
                    [stripped_raw_req]
                    if not stripped_raw_req.startswith("-r ")
                    else parse_requirements(
                        Path.cwd().joinpath(stripped_raw_req[len("-r ") :].strip())
                    )
                )

                reqs = [*reqs, *expanded_reqs]

    return reqs


def make_extra_requirements() -> Mapping[str, str]:
    extra_requirements = {}
    for req_file_path in Path(__file__).parent.glob("requirements-*.txt"):
        if req_file_path.name not in ["requirements-dev.txt", "requirements-test.txt"]:
            extra_req_name = req_file_path.name[len("requirements-") : -len(".txt")]
            extra_requirements = {
                **extra_requirements,
                extra_req_name: parse_requirements(req_file_path),
            }

    return extra_requirements


version = os.environ["PKG_VERSION"]


setup(
    author="Dimitrios Dedoussis",
    author_email="dimitrios@dedouss.is",
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 4 - Beta",
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
    package_data={
        "asynction": ["py.typed"],
        "asynction.templates": ["index.html.j2"],
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
            "documentation",
            "docs",
            "playground",
        ]
    ),
    name="asynction",
    packages=find_packages(include=["asynction", "asynction.*"]),
    entry_points={"console_scripts": ["asynction = asynction.__main__:main"]},
    url="https://github.com/dedoussis/asynction",
    version=version,
    zip_safe=True,
)
