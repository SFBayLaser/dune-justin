#!/bin/bash
# Local FD supera-stage comparison, baseline vs new builder, on the 27 Aug detsim file.
# Usage (on the laptop, outside the container):  SpacePointStudy/run_fd_local.sh [NEVENTS]   (default 40)
# Outputs: FD/localtest40/{baseline,new}/ (run.log, time.log, larcv.root) and truth_compare.json
N=${1:-40}
DRIVE=/run/media/usher/Drive2; R=$DRIVE/DUNE
exec apptainer exec -B /cvmfs,$DRIVE,$DRIVE:/media/usher/Drive2 --ipc --pid ~/test/fnal-dev-sl7.sif bash -c "
source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh > /dev/null 2>&1
cd $R/FD/v10_24_00d00
source ./localProducts_larsoft_v10_24_00_e26_prof/setup > /dev/null 2>&1
setup dunesw v10_24_00d00 -q e26:prof > /dev/null 2>&1
export FHICL_FILE_PATH=$R/dune-justin/DUNESpineWorkshop2026/fhicl:\$FHICL_FILE_PATH
W=$R/FD/localtest40; IN=$R/FD/workarea/GenMPVMPR_20260826T182831_g4_detsim.root
for v in baseline new; do
  f=standard_mythical_supera_dune10kt_1x2x6.fcl; [ \$v = baseline ] && f=standard_mythical_supera_dune10kt_1x2x6_baseline.fcl
  mkdir -p \$W/\$v; cd \$W/\$v; echo \"start \$v \$(date +%T)\"
  /usr/bin/time -v lar -c \$f -s \$IN -n $N > run.log 2> time.log; echo \"rc=\$? end \$v \$(date +%T)\"
done
source $R/dune-justin/SpacePointStudy/larcv_env.sh
python3 $R/dune-justin/SpacePointStudy/compare_truth.py baseline=\$W/baseline/larcv.root new=\$W/new/larcv.root --json \$W/truth_compare.json 2>&1 | grep -v '^Error in\|FileEntry\|requested to autoload\|^\$'
"
