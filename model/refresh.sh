#!/usr/bin/env bash
# Re-run the tracker and copy the page's data files into ../data.
set -euo pipefail
cd "$(dirname "$0")"
python3 model.py
python3 export.py
for id in chances trend polls latest leans_wide eday summary history parliament maori close_seats markets; do
  cp "out/$id.json" "../data/$id.json"
done
echo "data updated"
