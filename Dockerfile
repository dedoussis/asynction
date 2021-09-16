FROM python AS build-image

ARG VERSION

RUN pip install asynction[cli]==${VERSION}

FROM python:slim

COPY --from=build-image /usr/local/ /usr/local/

LABEL is.dedouss.asynction.maintainer="Dimitrios Dedoussis"
LABEL is.dedouss.asynction.maintainer_email="dimitrios@dedouss.is"

WORKDIR /opt/asynction

ENTRYPOINT ["python", "-m", "asynction"]
