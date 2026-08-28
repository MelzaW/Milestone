#!/bin/bash
# Rebuild the data from the CSVs and photographs, then put it on the live site.
# Run this after adding a photograph or a building.
set -e
cd "$(dirname "$0")"
python3 build.py

# Cache-bust every local asset. GitHub Pages lets browsers cache scripts and
# stylesheets, so without this a returning visitor keeps running the old app.js
# after a deploy and never sees the change.
STAMP=$(date +%s)
python3 - "$STAMP" <<'PY'
import re, sys
stamp = sys.argv[1]
h = open('index.html').read()
h = re.sub(r'\?v=[A-Za-z0-9]*(?=")', '?v=' + stamp, h)
open('index.html','w').write(h)
print(f"cache-busted assets with ?v={stamp}")
PY

git add -A
git commit -m "${1:-update}" || { echo "nothing changed"; exit 0; }
git push origin main
echo
echo "Pushed. Live in a minute or two at https://melzaw.github.io/Milestone/"
