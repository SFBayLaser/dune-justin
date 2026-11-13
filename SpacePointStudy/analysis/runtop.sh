#!/bin/bash
# usage: runtop.sh name "fcl lines"  -- builds points with the Fast tool (8 events) then dumps the ball-label table
H=/run/media/usher/Drive2/DUNE/samples/FD_330003/hitscan_loose; S=/run/media/usher/Drive2/DUNE/dune-justin/SpacePointStudy
n=$1; mkdir -p $H/$n; cd $H/$n
printf '#include "sp_hit_dune10kt_1x2x6.fcl"\nphysics.producers.cluster3d: @local::standard_spacepointbuilderdune\nphysics.producers.cluster3d.Hit3DBuilderAlg.MaxHitChiSquare: 10.0\n%b\n' "$2" > point.fcl
apptainer exec -B /cvmfs,/run/media/usher/Drive2,/run/media/usher/Drive2:/media/usher/Drive2 --ipc --pid ~/test/fnal-dev-sl7.sif bash -c "
source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh > /dev/null 2>&1
cd /run/media/usher/Drive2/DUNE/FD/v10_24_00d00
source ./localProducts_larsoft_v10_24_00_e26_prof/setup > /dev/null 2>&1
setup dunesw v10_24_00d00 -q e26:prof > /dev/null 2>&1
cd $H/$n
FHICL_FILE_PATH=$H/$n:/run/media/usher/Drive2/DUNE/dune-justin/DUNESpineWorkshop2026/fhicl:\$FHICL_FILE_PATH /usr/bin/time -v lar -c point.fcl -s /run/media/usher/Drive2/DUNE/samples/FD_330003/FD_330003_g4_detsim_supera.root -n 8 > run.log 2> time.log
echo lar done \$?
source $S/gallery_env.sh
python3 $S/sp_truth_dep.py $H/$n --sim-file /run/media/usher/Drive2/DUNE/samples/FD_330003/FD_330003_g4_detsim_supera.root --cache $H/truth_ide_cache.pkl --events 8 --dump --ball --ball-recall --ball-recall-r 1 --ball-recall-f 0.05 0.2 > dep.log 2>&1
echo dump done \$?
"
