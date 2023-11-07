# syntax=docker/dockerfile:1.6.0
FROM python:3.12.0-slim-bookworm AS brfast-base-image

# ============================ Configuration part ==============================

# - Configure pip to not check the latest version (this saves time).
# - Poetry is configured to:
#   - Have no interaction through the terminal (as we install it in a container)
#   - Create the virtualenv if there is none, and in this project
#   - Use the /tmp/poetry_cache directory as cache (used with BuildKit to
#     mutualize the python downloaded packages)
# - Set the Flask application as the webserver of BrFAST
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    FLASK_APP=brfast.webserver.application

# The parameters of the non-root user that is created to run this project
ARG USERNAME=brfast
ARG USER_UID=1001
ARG USER_GID=${USER_UID}

# ================================ Root part ===================================

# - Create the non-root user
# - Update the base packages, and install Poetry (we use the BuildKit caches to
#   mutualize the packages downloaded by apt and pip)
# - Remove the temporary files
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    groupadd --gid ${USER_GID} ${USERNAME} && \
    useradd --no-log-init --uid ${USER_UID} --gid ${USER_GID} --create-home ${USERNAME} && \
    apt update && \
    apt upgrade -y && \
    apt dist-upgrade -y && \
    pip install --upgrade pip poetry && \
    apt autoremove -y && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

# ============================== Non-root part =================================

# This container is ran as the non-root user for security reasons
USER ${USERNAME}

WORKDIR /app

# First, copy the files required by Poetry to install the module
COPY --chown=${USERNAME} README.md .
COPY --chown=${USERNAME} pyproject.toml .

# Just create an empty python project and install the module dependencies
RUN mkdir brfast && \
    touch brfast/__init__.py &&\
    poetry install --only main

# Copy the BrFAST sources and configuration file
COPY --chown=${USERNAME} brfast/ brfast/
COPY --chown=${USERNAME} config.ini.template config.ini


FROM brfast-base-image AS test-image

# Install the development dependencies
RUN poetry install --with dev

# Copy the BrFAST test sources
COPY --chown=${USERNAME} tests/ tests/

# The default command is to launch the tests
CMD ["poetry", "run", "coverage", "run", "-m", "unittest", "discover", "-s", "tests"]


FROM brfast-base-image

# Launch the Flask application as the default command
CMD ["poetry", "run", "python", "-m", "flask", "run"]