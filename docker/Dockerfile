FROM --platform=${BUILDPLATFORM} python:3.11-slim-buster

WORKDIR /app

COPY ../requirements.txt .

RUN apt-get update && \
    apt-get install --no-install-recommends -y git libicu-dev && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

ARG GIT_USER_NAME
ARG GIT_USER_EMAIL

RUN git config --global user.name "$GIT_USER_NAME" && \
    git config --global user.email "$GIT_USER_EMAIL"

COPY ../OSA/ OSA/
COPY ../main.py .

ENTRYPOINT ["python", "main.py"]
