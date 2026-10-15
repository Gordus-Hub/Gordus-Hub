FROM debian:13-slim

ARG DEBIAN_FRONTEND=noninteractive
ARG GORDUS_AI_SOURCE_SHA=UNBOUND

ARG GORDUS_AI_LOCK_SHA256=UNBOUND

ENV GORDUS_AI_SOURCE_SHA=${GORDUS_AI_SOURCE_SHA} \
    GORDUS_AI_LOCK_SHA256=${GORDUS_AI_LOCK_SHA256} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/opt/gordus-ai-venv/bin:${PATH}" \
    PYTHONPATH="/opt/gordus-ai/ai/runtime" \
    GORDUS_AI_DATA_ROOT=/var/lib/gordus-ai \
    ARGOS_PACKAGE_DIR=/var/lib/gordus-ai/argos-packages \
    STANZA_RESOURCES_DIR=/var/lib/gordus-ai/stanza_resources \
    GORDUS_AI_RUNTIME_SCOPE=THREE_PYTHON_LIBRARIES_INSTALLED_TASK_ASSETS_SEPARATELY_GATED

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
LABEL org.opencontainers.image.source="https://github.com/Gordus-Hub/Gordus-Hub" \
      org.opencontainers.image.title="Gordus AI three-library Python runtime" \
      org.gordus.ai.runtime.lock.sha256="${GORDUS_AI_LOCK_SHA256}"

# Materialize all three pinned libraries and every hash-locked transitive dependency
# in this reusable image. This installs neither packages on the user's host nor
# language/model/evaluation assets.
RUN test "${GORDUS_AI_LOCK_SHA256}" != "UNBOUND" \
    && printf '%s  %s\n' "${GORDUS_AI_LOCK_SHA256}" "ai/requirements/locks/runtime-py313-linux-x86_64.txt" | sha256sum --check - \
    && python3.13 -m venv /opt/gordus-ai-venv \
    && /opt/gordus-ai-venv/bin/python -m pip install --no-input --disable-pip-version-check --no-cache-dir --require-hashes -r ai/requirements/locks/runtime-py313-linux-x86_64.txt \
    && /opt/gordus-ai-venv/bin/python -m pip check \
    && /opt/gordus-ai-venv/bin/python - <<'PY'
from importlib.metadata import version
from argostranslate import package, translate
from cltk import NLP
import inspect_ai
import stanza
import torch

expected = {
    "argostranslate": "1.11.0",
    "cltk": "2.5.1",
    "inspect-ai": "0.3.280",
    "PyYAML": "6.0.2",
    "torch": "2.14.1+cpu",
}
for name, wanted in expected.items():
    actual = version(name)
    if actual != wanted:
        raise SystemExit(f"{name}: expected {wanted}, got {actual}")
if not callable(NLP) or not callable(translate.get_installed_languages):
    raise SystemExit("Required library APIs are not callable")
if torch.version.cuda is not None:
    raise SystemExit(f"CPU-only runtime required, got CUDA {torch.version.cuda}")
print("THREE_LIBRARY_IMPORT_AND_PIN_CHECK=PASS")
PY
RUN /opt/gordus-ai-venv/bin/inspect --version \
    && /opt/gordus-ai-venv/bin/python -m unittest discover -s /opt/gordus-ai/ai/runtime/tests -v \
    && chown -R root:root /opt/gordus-ai /opt/gordus-ai-venv \
    && chmod -R a=rX /opt/gordus-ai /opt/gordus-ai-venv

USER ai
WORKDIR /opt/gordus-ai
CMD ["bash"]
