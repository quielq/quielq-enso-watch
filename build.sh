#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "== 1/2 Provincial alert levels =="
python3 scripts/01_build_provincial_alerts.py

echo "== 2/2 Interactive map =="
python3 scripts/02_assemble_map.py

echo
echo "Done. Output: output/ph_el_nino_watch.html"
