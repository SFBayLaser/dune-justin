#!/usr/bin/env bash
set -euo pipefail

# 0) Environment (run on dunegpvm typically)
source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh
setup justin

# 1) Create a draft workflow (example: 20 MC jobs in stage 1)
WFID=$(justin create-workflow --description "toy 3-stage workflow" --monte-carlo 20 \
  | awk '/Workflow ID/ {print $NF}')

echo "Created workflow WFID=${WFID}"

# 2) Stage 1
justin create-stage --workflow-id "$WFID" --stage-id 1 \
  --jobscript-git SFBayLaser/dune-justin/testing/multistep/StageA.jobscript:main \
  --wall-seconds 7200 --rss-mib 2000 \
  --output-pattern-next-stage "gen_*.root"

# 3) Stage 2 (consumes stage 1 outputs automatically)
justin create-stage --workflow-id "$WFID" --stage-id 2 \
  --jobscript-git SFBayLaser/dune-justin/testing/multistep/StageB.jobscript:main \
  --wall-seconds 14400 --rss-mib 4000 \
  --output-pattern-next-stage "g4_*.root"

# 4) Stage 3 (final stage outputs)
justin create-stage --workflow-id "$WFID" --stage-id 3 \
  --jobscript-git SFBayLaser/dune-justin/testing/multistep/StageC.jobscript:main \
  --wall-seconds 7200 --rss-mib 4000 \
  --output-pattern "detsim_*.root"

# 5) Submit the workflow
justin submit-workflow --workflow-id "$WFID"
echo "Submitted workflow WFID=${WFID}"

# 6) Optional: show summary
justin show-stages --workflow-id "$WFID"
