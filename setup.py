#!/usr/bin/env python

from setuptools import find_packages
from setuptools import setup

with open("README.md") as readme_file:
    readme = readme_file.read()

with open("requirements.txt") as requiremets_file:
    requirements = requiremets_file.read().split()


setup(
    author="Dimitrios Dedoussis",
    author_email="ddedoussis@gmail.com",
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
    license="MIT license",
    long_description=readme,
    long_description_content_type="text/markdown",
    include_package_data=True,
    package_data={
        "asynction": ["py.typed"],
    },
    keywords="asyncapi openapi oai swagger rest api oauth flask microservice framework",
    name="asynction",
    packages=find_packages(include=["asynction", "asynction.*"]),
    url="https://github.com/dedoussis/asynction",
    version="0.0.1",
    zip_safe=False,
)
