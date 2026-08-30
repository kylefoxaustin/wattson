#!/usr/bin/env bash
# 50-app validation, QEMU side: TWO passes per app (pf-on for reads, base for
# writes) into out50/<label>.pf.json / .base.json.
set -eu
cd "$(dirname "$0")"
mkdir -p out50
grep -vE '^\s*(#|$)' manifest50.txt | sed 's/\s*#.*$//' | while read -r LABEL CMD; do
    [ -s "out50/$LABEL.pf.json" ] && [ -s "out50/$LABEL.base.json" ] && { echo "skip $LABEL"; continue; }
    echo "── $LABEL $(date +%H:%M:%S)"
    PFETCH=16 ./run-qemu.sh "$LABEL" -- $CMD > "out50/$LABEL.pf.json" || echo "  $LABEL PF-FAIL"
    ./run-qemu.sh "$LABEL" -- $CMD > "out50/$LABEL.base.json" || echo "  $LABEL BASE-FAIL"
done
echo VALIDATE50-QEMU-DONE
