# We do a multi-stage build (requires Docker >= 17.05) to install everything, then copy it all
# to the final target image.

# NOTE: psycopg2-binary won't install into Alpine because pg_config is missing, and to install that,
# we need a full development environment :-/
#   https://github.com/psycopg/psycopg2/issues/684

FROM python:alpine3.7 AS base

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

FROM base AS build

# install the requirements
# NOTE: psycopg2 needs postgresql-dev and build tools, lxml needs libxslt
RUN apk update && apk add --no-cache postgresql-dev gcc python3-dev musl-dev && apk add --no-cache libxslt-dev

# install the application requirements
COPY requirements.txt /tmp/
RUN pip install --upgrade pip
RUN pip install -r /tmp/requirements.txt

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

FROM base

# copy the application requirements
RUN pip install --upgrade pip
RUN apk add libxslt
COPY --from=build /usr/local/lib/python3.7/site-packages /usr/local/lib/python3.7/site-packages

# install the application
WORKDIR /app
COPY asl_articles asl_articles
COPY setup.py requirements.txt requirements-dev.txt run_server.py LICENSE.txt ./
RUN pip install -e .

# copy the config files
ARG ENABLE_TESTS
COPY asl_articles/config/logging.yaml.example asl_articles/config/logging.yaml
COPY docker/config/* asl_articles/config/
RUN rm -f asl_articles/config/debug.cfg

# copy the alembic files (so that users can upgrade their database)
COPY alembic alembic

# launch the web server
EXPOSE 5000
ENV DBCONN undefined
CMD [ "python", "/app/run_server.py" ]
