FROM python:3.7
WORKDIR /usr/app
ADD . /usr/app
RUN python -m pip install --upgrade pip setuptools
RUN make all-install
RUN pre-commit install
# initializes all pre-commit envs
RUN pre-commit