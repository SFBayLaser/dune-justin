#!/bin/bash
# Local gen -> g4 -> detsim -> supera (new builder, first pass) in the SL7 container, mirroring the justIN jobscripts.
# Usage (host): make_sample_local.sh FD|VD RUN NEVENTS [GEN_FCL]     e.g. make_sample_local.sh VD 20001 20
# Output: $R/{FD,VD}_samples/<det>_<RUN>/  (*_gen.root, *_g4.root, *_detsim.root, *_supera.root, larcv.root, logs)
DET=$1; RUN=$2; N=$3; GENFCL=${4:-}
DRIVE=/run/media/usher/Drive2; R=$DRIVE/DUNE; J=$R/dune-justin
if [ $DET = FD ]; then
  FD=$J/DUNESpineWorkshop2026/fhicl; GEN=mpvmpr_gen_1x2x6.fcl; G4=standard_g4_dune10kt_1x2x6.fcl
  DS=standard_detsim_dune10kt_1x2x6.fcl; SU=standard_mythical_supera_dune10kt_1x2x6.fcl
else
  FD=$J/DUNEVD/fhicl; GEN=mpvmpr_gen_vd_1x8x6.fcl; G4=standard_g4_dunevd10kt_1x8x6_3view_30deg.fcl
  DS=standard_detsim_dunevd10kt_1x8x6_3view_30deg.fcl; SU=standard_supera_dunevd10kt_1x8x6_3view_30deg.fcl
fi
[ -n "$GENFCL" ] && GEN=$GENFCL
W=$R/samples/${DET}_$RUN; mkdir -p $W
apptainer exec -B /cvmfs,$DRIVE,$DRIVE:/media/usher/Drive2 --ipc --pid ~/test/fnal-dev-sl7.sif bash -c "
source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh >/dev/null 2>&1
cd $R/FD/v10_24_00d00; source ./localProducts_larsoft_v10_24_00_e26_prof/setup >/dev/null 2>&1
setup dunesw v10_24_00d00 -q e26:prof >/dev/null 2>&1
export FHICL_FILE_PATH=$FD:\$FHICL_FILE_PATH
cd $W
step() { n=\$1; shift; echo \"start \$n \$(date +%T)\"; /usr/bin/time -v \"\$@\" > \$n.log 2> \$n.time; rc=\$?; echo \"\$n rc=\$rc \$(date +%T)\"; [ \$rc = 0 ] || exit \$rc; }
step gen    lar -c $GEN -n $N -e $RUN:0:1 -o ${DET}_${RUN}_gen.root
step g4     lar -c $G4 -s ${DET}_${RUN}_gen.root -o ${DET}_${RUN}_g4.root -n -1
step detsim lar -c $DS -s ${DET}_${RUN}_g4.root -o ${DET}_${RUN}_g4_detsim.root -n -1
step supera lar -c $SU -s ${DET}_${RUN}_g4_detsim.root -n -1
" > $W/driver.log 2>&1
echo "done $DET $RUN rc=$?" >> $W/driver.log
