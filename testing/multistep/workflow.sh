#!/bin/bash
#set -euo pipefail

# ---- user knobs ----
NGEN=5
JOBSCRIPT_REF=main
REPO="SFBayLaser/dune-justin"   # repo that holds your jobscripts

# Output filename patterns produced by each stage
GEN_OUT="*_gen.root"
G4_OUT="*_g4.root"
DETSIM_OUT="*_detsim.root"
RECO_OUT="*_reco.root"
LARCV_OUT="*_larcv.root"

# ---- environment ----
#export prod_db=/cvmfs/dune.opensciencegrid.org/products/dune
#test -d "$prod_db" || { echo "prod_db path not found: $prod_db"; exit 2; }

echo "Attempting to set up the dune environment"
source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh
echo "Returned from setup"

setup justin

# If needed (first time on a node), do:
#   justin time
#   justin get-token

# ---- create workflow (draft) ----
WFID=$(
  justin create-workflow --description "gen->reco test" --monte-carlo "${NGEN}" 
)
echo "WFID=${WFID}"

# ---- stage 1: GEN ----
justin create-stage --workflow-id "${WFID}" --stage-id 1 \
  --jobscript-git "${REPO}/testing/multistep/gen.jobscript:${JOBSCRIPT_REF}" \
  --wall-seconds 14400 --rss-mib 4000 \
  --env NEVENTS=20 \
  --env JOB_FHICL_FILE="prod_muminus_0.1-5.0GeV_isotropic_dune10kt_1x2x6.fcl" \
  --output-pattern-next-stage "${GEN_OUT}" \
  --lifetime-days 1

# ---- stage 2: G4 (consumes stage-1 outputs automatically) ----
justin create-stage --workflow-id "${WFID}" --stage-id 2 \
  --jobscript-git "${REPO}/testing/multistep/g4.jobscript:${JOBSCRIPT_REF}" \
  --env JOB_FHICL_FILE="standard_g4_dune10kt_1x2x6.fcl" \
  --wall-seconds 28800 --rss-mib 8000 \
  --output-pattern-next-stage "${G4_OUT}" \
  --lifetime-days 1

# ---- stage 3: DETSIM (consumes stage-2 outputs automagically) ----
justin create-stage --workflow-id "${WFID}" --stage-id 3 \
  --jobscript-git "${REPO}/testing/multistep/detsim.jobscript:${JOBSCRIPT_REF}" \
  --env JOB_FHICL_FILE="standard_detsim_dune10kt_1x2x6.fcl" \
  --wall-seconds 28800 --rss-mib 8000 \
  --output-pattern-next-stage "${DETSIM_OUT}" \
  --lifetime-days 1

# ---- stage 4: Reconstruction (final outputs) ----
justin create-stage --workflow-id "${WFID}" --stage-id 4 \
  --jobscript-git "${REPO}/testing/multistep/reco.jobscript:${JOBSCRIPT_REF}" \
  --env JOB_FHICL_FILE="standard_supera_dune10kt_1x2x6.fcl" \
  --wall-seconds 28800 --rss-mib 8000 \
  --output-pattern "${RECO_OUT}" \
  --output-pattern "${LARCV_OUT}" \
  --lifetime-days 1

# ---- submit ----
justin submit-workflow --workflow-id "${WFID}"
echo "Submitted WFID=${WFID}"

# ---- monitor helpers ----
justin show-stages --workflow-id "${WFID}"
# justin show-jobs --workflow-id "${WFID}"
