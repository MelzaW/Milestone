#!/bin/bash
# Rebuild the data from the CSVs and photographs, then put it on the live site.
# Run this after adding a photograph or a building.
set -e
cd "$(dirname "$0")"
python3 build.py
git add -A
git commit -m "${1:-update}" || { echo "nothing changed"; exit 0; }
git push origin main
echo
echo "Pushed. Live in a minute or two at https://melzaw.github.io/Milestone/"
