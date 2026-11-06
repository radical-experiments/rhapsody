#!/bin/bash
# HPPSS W1 runs, inside a 1-node CPU allocation
source $PSCRATCH/hppss/env.sh
export OPENFOAM_CASE_DIR=$PSCRATCH/hppss/runs/openfoam-cases
summarize() {  # per-case solver time = last ExecutionTime in the case's simpleFoam log
    for d in run-pD-*; do
        t=$(grep -h "^ExecutionTime" $(grep -l "^Case.*$d\$" rhapsody.session.*/task.*.stdout 2>/dev/null) 2>/dev/null | tail -1)
        echo "$d ${t:-NO-ExecutionTime}"
    done
}
for drv in ${DRIVERS:-staged video}; do
    w=$PSCRATCH/hppss/runs/$drv; rm -rf $w; cp -r $PSCRATCH/hppss/runs/pitzDaily-optimize $w; cd $w
    echo "=== $drv start $(date +%T) on $(hostname)"
    /usr/bin/time -v dragon driver-$drv.py > $drv.log 2>&1
    echo "=== $drv rc=$? end $(date +%T)"
    grep -E '^Iteration|WARNING|Traceback|Error' $drv.log | head -40
    grep -E 'Elapsed \(wall' $drv.log
    summarize > case-times.txt; cat case-times.txt
done
