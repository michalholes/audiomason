FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg p7zip-full unrar-free unzip rsync ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
COPY audiomason /app/audiomason

RUN pip install --no-cache-dir -U pip \
 && pip install --no-cache-dir .

ENTRYPOINT ["audiomason"]
