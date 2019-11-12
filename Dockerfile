# NOTE: psycopg2-binary won't install into Alpine because pg_config is missing, and to install that,
# we need a full development environment :-/
# We do a multi-stage build (requires Docker >= 17.05) to install everything, then copy it all
# to the final target image.
#   https://github.com/psycopg/psycopg2/issues/684

FROM python:alpine3.7 AS base

# install the requirements
FROM base AS build
RUN mkdir /install
RUN apk update && apk add postgresql-dev gcc python3-dev musl-dev
WORKDIR /install
COPY requirements.txt /tmp/
RUN pip install --upgrade pip
RUN pip install --install-option="--prefix=/install" -r /tmp/requirements.txt

FROM base

# copy the Python requirements
COPY --from=build /install /usr/local
RUN apk --no-cache add libpq
RUN pip install --upgrade pip

# install the application
WORKDIR /app
ADD asl_articles asl_articles
COPY setup.py requirements.txt requirements-dev.txt run_server.py LICENSE.txt ./
RUN pip install -e .

# copy the config files
ARG ENABLE_TESTS
COPY asl_articles/config/logging.yaml.example asl_articles/config/logging.yaml
COPY docker/config/* asl_articles/config/

# launch the web server
EXPOSE 5000
ENV DBCONN undefined
CMD [ "python", "/app/run_server.py" ]
