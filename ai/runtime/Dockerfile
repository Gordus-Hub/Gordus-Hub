FROM debian:13-slim

ARG DEBIAN_FRONTEND=noninteractive

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    GORDUS_AI_DATA_ROOT=/var/lib/gordus-ai \
    ARGOS_PACKAGES_DIR=/var/lib/gordus-ai/argos-packages \
    STANZA_RESOURCES_DIR=/var/lib/gordus-ai/stanza_resources

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash ca-certificates curl git python3.13 python3.13-venv \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system ai \
    && useradd --system --gid ai --home-dir /home/ai --create-home ai \
    && install -d -o ai -g ai /var/lib/gordus-ai/argos-packages \
       /var/lib/gordus-ai/cltk /var/lib/gordus-ai/stanza_resources \
       /var/lib/gordus-ai/evaluations /workspace

WORKDIR /opt/gordus-ai
COPY ai /opt/gordus-ai/ai
COPY scripts/ai /opt/gordus-ai/scripts/ai
RUN chown -R root:root /opt/gordus-ai \
    && chmod -R a=rX /opt/gordus-ai

USER ai
WORKDIR /opt/gordus-ai
CMD ["bash"]
