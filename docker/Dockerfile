FROM --platform=${BUILDPLATFORM} python:3.11-slim-buster

WORKDIR /app

COPY ../requirements.txt .

RUN apt-get update && \
    apt-get install --no-install-recommends -y git && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

COPY ../OSA/ OSA/
COPY ../main.py .

ENV REPO_URL=""

CMD ["sh", "-c", "python main.py $REPO_URL"]