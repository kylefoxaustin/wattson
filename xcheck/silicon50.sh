#!/bin/sh
# 50-app validation, silicon side: perf (pinned) + DDR window per app.
set -eu
cd /tmp/xcheck50
mkdir -p out50
grep -vE '^[[:space:]]*(#|$)' manifest50.txt | sed 's/[[:space:]]*#.*$//' | while read -r LABEL CMD; do
    echo "── $LABEL"
    ./run-perf.sh "$LABEL" -- $CMD > "out50/$LABEL.hw.json" || echo "  $LABEL PERF-FAIL"
    ./run-ddr.sh  "$LABEL" -- $CMD > "out50/$LABEL.ddr.json" 2>/dev/null || echo "  $LABEL DDR-FAIL"
done
echo SILICON50-DONE
