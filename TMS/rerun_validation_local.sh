#!/bin/bash
# Run the two Tracking_Validation passes (legacy and Cluster3D) locally on chosen spills, for spills whose justIN
# validation stage did not produce output. The outputs get the same names as the grid job's, so merge_validation.sh
# picks them up.
#
#   ./rerun_validation_local.sh VERSION DIR SPILL [SPILL ...]
#
#   VERSION  v04 ... (upper case is accepted and lowered)
#   DIR      directory with the RecoCandidates files (or DIR/usertests); the outputs are written next to each input
#   SPILL    spill numbers, e.g. 33 42 178
#
# Example:  ./rerun_validation_local.sh v04 /exp/dune/data/users/usher/tmstest 33 42 178
#
# Set up the dune-tms environment first (source setup.sh in dune-tms, which sets TMS_DIR), so ROOT is available. The
# executable is $TMS_DIR/scripts/Validation/Tracking_Validation unless VALIDATION_EXE is set; use the build that matches the
# justIN tarball, so the local and grid outputs agree. Note the commit in your records: these files are not grid output.

VER=${1:?usage: rerun_validation_local.sh VERSION DIR SPILL [SPILL ...]}
DIR=${2:?usage: rerun_validation_local.sh VERSION DIR SPILL [SPILL ...]}
shift 2
(( $# > 0 )) || { echo "no spills given" >&2; exit 1; }
VER=${VER,,}
EXE=${VALIDATION_EXE:-${TMS_DIR:-}/scripts/Validation/Tracking_Validation}
[[ -x "$EXE" ]] || { echo "ERROR: Tracking_Validation not found at $EXE (set up dune-tms, or set VALIDATION_EXE)" >&2; exit 2; }
PREFIX=MiniProdN5p3_NDComplex_FHC.spill.full.sanddrift
STEM=EDEPSIM_SPILLS_TMSReco_Cluster3D_${VER}_RecoCandidates

failed=0
for spill in "$@"; do
  name=$(printf "%s.%07d.%s" "$PREFIX" "$((10#$spill))" "$STEM")
  in=""
  for d in "$DIR" "$DIR/usertests"; do [[ -s "$d/$name.root" ]] && in="$d/$name.root" && break; done
  [[ -n "$in" ]] || { echo "spill $spill: $name.root not found under $DIR" >&2; failed=$((failed+1)); continue; }
  out="${in%.root}"
  echo "spill $spill: validating $in"
  # -1 = all events, 5 = slices to draw (as in the grid job). Tracking_Validation writes a _images folder of plots next to
  # its output, so the outputs are made in a scratch directory and only the two ROOT files are moved into DIR.
  work=$(mktemp -d) || exit 1
  leaf=$(basename "$out")
  ( cd "$work" || exit 1
    "$EXE" "$in" -1 5 "$work/${leaf}_validation_legacy.root" > legacy.log 2>&1 \
      && TMS_VALIDATION_RECO_TREE=Reco_Tree_C3D TMS_VALIDATION_TRUTH_TREE=Truth_Info_C3D \
         "$EXE" "$in" -1 5 "$work/${leaf}_validation_cluster3d.root" > cluster3d.log 2>&1 )
  rc=$?
  if [[ $rc -ne 0 || ! -s "$work/${leaf}_validation_legacy.root" || ! -s "$work/${leaf}_validation_cluster3d.root" ]]; then
    echo "spill $spill: FAILED (logs kept in $work)" >&2; failed=$((failed+1))
  else
    mv "$work/${leaf}_validation_legacy.root" "$work/${leaf}_validation_cluster3d.root" "$(dirname "$in")/" && rm -rf "$work"
  fi
done
(( failed == 0 )) && echo "done" || { echo "$failed spills failed" >&2; exit 3; }
