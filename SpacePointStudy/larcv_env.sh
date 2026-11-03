# Source inside the SL7 container (needs -B /cvmfs). Gives PyROOT + the cvmfs larcv2 dictionaries.
#   apptainer exec -B /cvmfs,/run/media/usher/Drive2 ~/test/fnal-dev-sl7.sif \
#       bash -c 'source SpacePointStudy/larcv_env.sh && python3 SpacePointStudy/compare_truth.py ...'
source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh > /dev/null 2>&1
setup larcv2 v2_3_2 -q e26:p3915:prof > /dev/null 2>&1
# ROOT needs the headers to build the larcv class dictionaries for PyROOT
export ROOT_INCLUDE_PATH=$(find $LARCV2_INC/larcv -type d | tr '\n' ':')$LARCV2_INC
