#!/bin/bash
#SBATCH -N 1 -C cpu -q debug -t 00:20:00 -J hppss-part1
# Part 1: the pitzDaily optimization locally under Dragon on one node (video size)
source $HPPSS_WORK/my-env.sh
cd $HPPSS_WORK/part1
echo "=== start $(date +%T) on $(hostname)"
/usr/bin/time -v dragon driver-video.py > video.log 2>&1
echo "=== rc=$? end $(date +%T)"
grep -E '^Iteration|WARNING|Traceback|Error' video.log | head -20
grep -E 'Elapsed \(wall' video.log
