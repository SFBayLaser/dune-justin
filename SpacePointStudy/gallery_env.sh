#!/bin/bash
# Source inside the SL7 container: dunesw (local dunereco build) + gallery, for sp_truth_*.py
D=/run/media/usher/Drive2; R=$D/DUNE
source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh >/dev/null 2>&1
cd $R/FD/v10_24_00d00; source ./localProducts_larsoft_v10_24_00_e26_prof/setup >/dev/null 2>&1
setup dunesw v10_24_00d00 -q e26:prof >/dev/null 2>&1
setup gallery v1_22_06 -q e26:prof >/dev/null 2>&1
