FROM node:current-alpine3.13

ADD . /opt/asynction/example

WORKDIR /opt/asynction/example

RUN npm ci

EXPOSE 3000

ENTRYPOINT ["npm"]

CMD ["start"]
