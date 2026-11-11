#!/bin/bash
# Usage (host): run_sp_truth_pos.sh art_file.root [args for sp_truth_pos.py]
DRIVE=/run/media/usher/Drive2; R=$DRIVE/DUNE; S=$R/dune-justin/SpacePointStudy
F=$1; shift
apptainer exec -B /cvmfs,$DRIVE,$DRIVE:/media/usher/Drive2 --ipc --pid ~/test/fnal-dev-sl7.sif bash -c "
source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh >/dev/null 2>&1
cd $R/FD/v10_24_00d00; source ./localProducts_larsoft_v10_24_00_e26_prof/setup >/dev/null 2>&1
setup dunesw v10_24_00d00 -q e26:prof >/dev/null 2>&1
setup gallery v1_22_06 -q e26:prof >/dev/null 2>&1
python3 $S/${PYS:-sp_truth_pos.py} $F $*
"
