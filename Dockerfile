# We do a multi-stage build (requires Docker >= 17.05) to install everything, then copy it all
# to the final target image.

FROM centos:8 AS base

# update packages and install Python
RUN dnf -y upgrade-minimal && \
    dnf install -y python38 && \
    dnf clean all

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

FROM base AS build

# set up a virtualenv
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip

# install the application requirements
COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

FROM base

# copy the virtualenv from the build image
COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

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

# NOTE: We set these so that we can update the database outside the container.
ENV UID=$DOCKER_UID
ENV GID=$DOCKER_GID

# launch the web server
EXPOSE 5000
ENV DBCONN undefined
CMD [ "python", "/app/run_server.py" ]
