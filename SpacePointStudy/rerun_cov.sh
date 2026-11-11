#!/bin/bash
# rerun the deposit-level evaluation (now with coverage) on all points of a finished hit scan: rerun_cov.sh scan_outdir sim_file
O=$1; S=$2; H=$(dirname $0); H=$(cd $H && pwd)
source $H/gallery_env.sh
names=$(cd $O && ls -d */ | tr -d /)
first=$(echo $names | cut -d' ' -f1); rest=$(echo $names | cut -d' ' -f2-)
python3 $H/sp_truth_dep.py $O/$first --sim-file $S --cache $O/truth_ide_cache.pkl 2>&1 | grep -v '^Error in\|autoload' > $O/$first/dep_eval.json.log
printf '%s\n' $rest | xargs -P 6 -I{} sh -c "python3 $H/sp_truth_dep.py $O/{} --sim-file $S --cache $O/truth_ide_cache.pkl > $O/{}/dep_eval.json.log 2>&1"
python3 $H/sp_truth_dep.py --table $(for n in $names; do echo $O/$n; done) --cov | tee $O/cov_table.txt
