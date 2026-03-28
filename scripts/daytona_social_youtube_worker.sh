#!/usr/bin/env bash
# Run inside a Daytona sandbox after `git clone` (repo root = cwd).
# Playwright-only agent: no LLM / no OPENAI_API_KEY in the sandbox.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CHANNEL_URL="${CHANNEL_URL:-https://www.youtube.com/@YouTube/videos}"
MAX_ITEMS="${MAX_ITEMS:-10}"
OUTPUT="${OUTPUT:-/tmp/social_snapshot.finding.json}"
MOCK="${MOCK:-}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found" >&2
  exit 1
fi

python3 -m pip install -q --upgrade pip setuptools wheel

if [ "$MOCK" = "1" ] || [ "$MOCK" = "true" ]; then
  python3 -m pip install -q -e .
  python3 -m workers.social_public.cli \
    --channel-url "$CHANNEL_URL" \
    --max-items "$MAX_ITEMS" \
    -o "$OUTPUT" \
    --mock
else
  python3 -m pip install -q -e ".[worker]"
  python3 -m playwright install chromium
  python3 -m workers.social_public.cli \
    --channel-url "$CHANNEL_URL" \
    --max-items "$MAX_ITEMS" \
    -o "$OUTPUT" \
    --mode playwright
fi

echo "Wrote $OUTPUT" >&2
