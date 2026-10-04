#!/usr/bin/env bash
# Rebuild tables, diagrams and the Assignment 2 PDF.
# Requires: ../code/.venv (pandas, PyYAML), pypdf, pandoc, graphviz (dot), node + Google Chrome.
# Set NODE_TOOLS to a directory that already contains node_modules/puppeteer-core;
# otherwise it is installed into a temporary directory.
set -euo pipefail

REPORT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPORT_DIR"
PY="${PY:-../code/.venv/bin/python}"
CHROME_PATH="${CHROME_PATH:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
export CHROME_PATH

if [[ -z "${NODE_TOOLS:-}" ]]; then
  NODE_TOOLS="$(mktemp -d)"
  trap 'rm -rf "$NODE_TOOLS"' EXIT
  (cd "$NODE_TOOLS" && npm init -y >/dev/null && PUPPETEER_SKIP_DOWNLOAD=1 npm i --silent puppeteer-core)
fi
export NODE_PATH="$NODE_TOOLS/node_modules"

"$PY" scripts/make_tables.py
"$PY" scripts/verify_numbers.py

for f in diagrams/*.dot; do
  dot -Tpng -Gdpi=200 "$f" -o "figures/$(basename "$f" .dot).png"
done

python3 build/build_pdf.py "$@"
