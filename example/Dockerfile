FROM python AS build-image

ADD ./requirements.txt /opt/asynction/example/requirements.txt

WORKDIR /opt/asynction/example

RUN pip install -r requirements.txt

FROM python:slim

COPY --from=build-image /usr/local/ /usr/local/

LABEL is.dedouss.asynction.maintainer="Dimitrios Dedoussis"
LABEL is.dedouss.asynction.maintainer_email="dimitrios@dedouss.is"

ADD . /opt/asynction/example

WORKDIR /opt/asynction/example

EXPOSE 5000

ENTRYPOINT ["python", "app.py"]
