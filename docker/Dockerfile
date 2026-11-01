FROM --platform=${BUILDPLATFORM} python:3.11-slim-buster

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && \
    apt-get install --no-install-recommends -y git libicu-dev && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

ARG GIT_USER_NAME
ARG GIT_USER_EMAIL

RUN git config --global user.name "$GIT_USER_NAME" && \
    git config --global user.email "$GIT_USER_EMAIL"

COPY osa_tool/ osa_tool/
COPY docker/entrypoint.sh ./docker-entrypoint.sh
RUN chmod +x ./docker-entrypoint.sh

# The container cannot inherit a logged-in host command from the user's machine.
# Keep bare Docker runs on the API-key transport, but leave custom provider
# arguments and custom config files in control when the user supplies them.
ENTRYPOINT ["./docker-entrypoint.sh"]
