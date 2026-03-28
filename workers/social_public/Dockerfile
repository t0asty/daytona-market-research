# Daytona snapshot image: public YouTube listing worker (Playwright Chromium).
# Build from repo root: docker build -f workers/social_public/Dockerfile -t daytona-social-youtube .
FROM python:3.12-slim-bookworm

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /workspace/
COPY report_gen /workspace/report_gen/
COPY workers /workspace/workers/

RUN pip install --no-cache-dir pip setuptools wheel \
    && pip install --no-cache-dir -e ".[worker]" \
    && playwright install --with-deps chromium

ENV PYTHONUNBUFFERED=1

# Default: print help; Daytona `execute_command` should invoke the worker explicitly, e.g.:
# python -m workers.social_public.cli --channel-url "https://www.youtube.com/@YouTube/videos" -o /tmp/social_snapshot.finding.json
CMD ["python", "-m", "workers.social_public.cli", "--help"]
