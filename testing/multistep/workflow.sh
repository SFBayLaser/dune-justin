#!/usr/bin/env bash
set -euo pipefail

# ---- user knobs ----
NGEN=5
JOBSCRIPT_REF=main
REPO="SFBayLaser/dune-justin"   # repo that holds your jobscripts

# Output filename patterns produced by each stage
GEN_OUT="gen_*.root"
G4_OUT="g4_*.root"
DETSIM_OUT="detsim_*.root"

# ---- environment ----
#export prod_db=/cvmfs/dune.opensciencegrid.org/products/dune
#test -d "$prod_db" || { echo "prod_db path not found: $prod_db"; exit 2; }

source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh
echo "After setup_dune.sh: PRODUCTS=${PRODUCTS:-unset}"
which ups || true
ups list -a dune* | head || true

setup justin

# If needed (first time on a node), do:
#   justin time
#   justin get-token

# ---- create workflow (draft) ----
WFID=$(
  justin create-workflow --description "gen->g4->detsim test" --monte-carlo "${NGEN}" \
  | awk '/Workflow ID/ {print $NF}'
)
echo "WFID=${WFID}"

# ---- stage 1: GEN ----
justin create-stage --workflow-id "${WFID}" --stage-id 1 \
  --jobscript-git "${REPO}/testing/multistep/gen.jobscript:${JOBSCRIPT_REF}" \
  --wall-seconds 14400 --rss-mib 4000 \
  --output-pattern-next-stage "${GEN_OUT}"

# ---- stage 2: G4 (consumes stage-1 outputs automatically) ----
justin create-stage --workflow-id "${WFID}" --stage-id 2 \
  --jobscript-git "${REPO}/testing/multistep/g4.jobscript:${JOBSCRIPT_REF}" \
  --wall-seconds 28800 --rss-mib 8000 \
  --output-pattern-next-stage "${G4_OUT}"

# ---- stage 3: DETSIM (final outputs) ----
justin create-stage --workflow-id "${WFID}" --stage-id 3 \
  --jobscript-git "${REPO}/testing/multistep/detsim.jobscript:${JOBSCRIPT_REF}" \
  --wall-seconds 28800 --rss-mib 8000 \
  --output-pattern "${DETSIM_OUT}"

# ---- submit ----
justin submit-workflow --workflow-id "${WFID}"
echo "Submitted WFID=${WFID}"

# ---- monitor helpers ----
justin show-stages --workflow-id "${WFID}"
# justin show-jobs --workflow-id "${WFID}"
