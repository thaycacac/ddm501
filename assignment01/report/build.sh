#!/usr/bin/env bash
# Rebuild figures and the Assignment 1 PDF.
# Requires: python3 (pandas, scikit-learn, matplotlib, pypdf), pandoc, graphviz (dot), node + Google Chrome.
# Set NODE_TOOLS to a directory that already contains node_modules/{@mermaid-js/mermaid-cli,puppeteer-core};
# otherwise they are installed into a temporary directory.
set -euo pipefail

REPORT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPORT_DIR"
CHROME_PATH="${CHROME_PATH:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
export CHROME_PATH

if [[ -z "${NODE_TOOLS:-}" ]]; then
  NODE_TOOLS="$(mktemp -d)"
  trap 'rm -rf "$NODE_TOOLS"' EXIT
  (cd "$NODE_TOOLS" && npm init -y >/dev/null && PUPPETEER_SKIP_DOWNLOAD=1 npm i --silent @mermaid-js/mermaid-cli puppeteer-core)
fi
export NODE_PATH="$NODE_TOOLS/node_modules"

python3 scripts/data_profile.py >/dev/null
python3 scripts/feasibility_check.py >/dev/null
python3 scripts/plot_segments.py

for f in diagrams/*.dot; do
  dot -Tpng -Gdpi=220 "$f" -o "figures/$(basename "$f" .dot).png"
done

printf '{"executablePath":"%s","args":["--no-sandbox"]}' "$CHROME_PATH" > "$NODE_TOOLS/puppeteer.json"
for f in diagrams/*.mmd; do
  "$NODE_TOOLS/node_modules/.bin/mmdc" -p "$NODE_TOOLS/puppeteer.json" -i "$f" \
    -o "figures/$(basename "$f" .mmd).png" -s 3 -b white
done

python3 build/build_pdf.py "$@"
