#!/bin/bash
# Usage (on the host): compare_parallel.sh SCANDIR [JOBS] [tol...]
# One compare_truth process per point (inside the SL7 container), merged into SCANDIR/compare.json
S=$(readlink -f $1); J=${2:-16}; shift 2; TOL=${@:-1 2}
HERE=$(dirname $(readlink -f $0)); D=/run/media/usher/Drive2
mkdir -p $S/cmp
apptainer exec -B /cvmfs,$D --ipc --pid ~/test/fnal-dev-sl7.sif bash -c "
source $HERE/larcv_env.sh >/dev/null 2>&1
ls -d $S/*/ | xargs -n1 basename | grep -v '^cmp\$' | xargs -P $J -I{} sh -c '[ -s $S/cmp/{}.json ] || python3 $HERE/compare_truth.py {}=$S/{}/larcv.root --tol $TOL --json $S/cmp/{}.json > $S/cmp/{}.txt 2>$S/cmp/{}.err'
"
python3 - $S <<'P'
import json,glob,sys
S=sys.argv[1]; d={}
for f in sorted(glob.glob(S+"/cmp/*.json")): d.update(json.load(open(f)))
json.dump(d,open(S+"/compare.json","w"),indent=1); print(len(d),"points merged")
P
