#!/bin/zsh
# Builds the indexes of one case's arms (each family's arm_build_<F>: the Graphify graph, the Trail map …), one at a time
# (RAM), with time and peak memory in $B/<tid>/build.log. An arm whose clone does not exist is skipped.
# Usage: build.sh <tid> [arm ...]     (default arms: ARMS of stand.env)
H=${0:A:h}; source $H/lib.sh
TID=$1; shift; ARMS_TO=($@); [ ${#ARMS_TO} -eq 0 ] && ARMS_TO=($ARM_LIST)
D=$B/$TID; LOG=$D/build.log
for ARM in $ARMS_TO; do
  F=$(arm_family $ARM)
  [ -d $D/$ARM ] && has_hook arm_build $F && arm_build_$F $D/$ARM $D $LOG
done
true
