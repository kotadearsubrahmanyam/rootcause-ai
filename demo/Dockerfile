FROM python:3.12-slim AS deployed
WORKDIR /store
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir fastapi uvicorn httpx opentelemetry-sdk opentelemetry-exporter-otlp-proto-http
COPY service.py inventory.py rename.patch ./
# Package the demo with its own reproducible two-release Git history.
ENV GIT_AUTHOR_NAME="Demo store" GIT_AUTHOR_EMAIL=demo@localhost GIT_COMMITTER_NAME="Demo store" GIT_COMMITTER_EMAIL=demo@localhost GIT_AUTHOR_DATE=2026-01-01T00:00:00Z GIT_COMMITTER_DATE=2026-01-01T00:00:00Z
RUN git init -q && git add service.py inventory.py && git commit -qm 'Healthy inventory response' && git apply rename.patch && git add inventory.py && git commit -qm 'Rename inventory response field'
FROM deployed AS validation
RUN pip install --no-cache-dir pytest && git config --system --add safe.directory "*"
COPY validation.py test_checkout.py /checks/
WORKDIR /checks
USER 65534:65534
CMD ["uvicorn","validation:app","--host","0.0.0.0","--port","8000"]

FROM deployed AS store
CMD ["uvicorn","service:app","--host","0.0.0.0","--port","8000"]
