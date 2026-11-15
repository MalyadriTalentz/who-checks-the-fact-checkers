#!/bin/sh
# Rebuild every number in the report from the snapshot and the committed judgments.
# Data download, page fetching and judging are separate, slower steps: see README.md.
set -e
.venv/bin/python analysis/part1.py data/raw
.venv/bin/python analysis/part2.py
.venv/bin/python analysis/figures.py
.venv/bin/python report/build.py
(cd report && tectonic -X compile report.tex)  # needs tectonic (brew install tectonic)
