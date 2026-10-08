#!/bin/bash
# Download the validation outputs of one reco version (v01, v02, v03, v04 ...) from rucio: for each spill, the legacy and the
# Cluster3D Tracking_Validation files made by the second stage (tms_validation.jobscript).
#
#   ./fetch_validation.sh VERSION [DIR] [FIRST] [LAST]
#
#   VERSION  v04 ... (the "Cluster3D_vNN" in the file name; upper case is accepted and lowered)
#   DIR      where the files go (default ./validation_VERSION); files already in DIR or DIR/usertests are skipped
#   FIRST, LAST   spill numbers to fetch (default 1 to 250)
#
# Examples:
#   ./fetch_validation.sh v04 ./validation_v04            # everything not on disk yet
#   ./fetch_validation.sh v04 ./validation_v04 229 229    # one spill
#   DRY_RUN=1 ./fetch_validation.sh v04 ./validation_v04  # only show what is missing, needs no rucio
#   WITH_LOG=1 ./fetch_validation.sh v04 ...              # also fetch the *_validation.log files (not needed for merging)
#
# Same behavior as fetch_reco.sh: skips what is already there, downloads the rest in chunks, repeats up to 3 passes, lists
# what is still missing, and makes DIR readable by everyone at the end (SHARE=0 to leave the permissions alone).
# Set up rucio and a valid token/proxy first, in the same shell.
#
# When all files are here, merge them with merge_validation.sh DIR.

set -u
umask 0002
VER=${1:?usage: fetch_validation.sh VERSION [DIR] [FIRST] [LAST]}
VER=${VER,,}                       # the file names have a lower case v
DIR=${2:-./validation_${VER}}
FIRST=${3:-1}
LAST=${4:-250}
RSE=${RSE:-DUNE_US_FNAL_DISK_STAGE}
SCOPE=usertests
PREFIX=MiniProdN5p3_NDComplex_FHC.spill.full.sanddrift
STEM=EDEPSIM_SPILLS_TMSReco_Cluster3D_${VER}_RecoCandidates
SUFFIXES=(${STEM}_validation_legacy.root ${STEM}_validation_cluster3d.root)
[ -n "${WITH_LOG:-}" ] && SUFFIXES+=(${STEM}_validation.log)
CHUNK=${CHUNK:-20}

mkdir -p "$DIR"
MISSING="$DIR/files_missing_validation_${VER}.txt"

list_missing() {
  : > "$MISSING"
  for i in $(seq "$FIRST" "$LAST"); do
    for suffix in "${SUFFIXES[@]}"; do
      name=$(printf "%s.%07d.%s" "$PREFIX" "$i" "$suffix")
      if [ ! -s "$DIR/$name" ] && [ ! -s "$DIR/$SCOPE/$name" ]; then
        echo "$SCOPE:$name" >> "$MISSING"
      fi
    done
  done
  wc -l < "$MISSING"
}

total=$(( (LAST - FIRST + 1) * ${#SUFFIXES[@]} ))
n=$(list_missing)
echo "$VER: $n of $total files are not in $DIR"
[ "$n" -eq 0 ] && exit 0
if [ -n "${DRY_RUN:-}" ]; then
  echo "dry run; list written to $MISSING"
  exit 0
fi
command -v rucio > /dev/null || { echo "rucio not found: set it up first (and a valid token or proxy)"; exit 2; }

for pass in 1 2 3; do
  echo "pass $pass: downloading $n files from $RSE"
  xargs -n "$CHUNK" rucio download --dir "$DIR" --no-subdir --rses "$RSE" < "$MISSING"
  n=$(list_missing)
  [ "$n" -eq 0 ] && break
done

[ "${SHARE:-1}" = "1" ] && chmod -R a+rX "$DIR" 2> /dev/null

if [ "$n" -eq 0 ]; then
  echo "$VER: all files are in $DIR"
else
  echo "$VER: $n files are still missing, listed in $MISSING"
  first=$(head -1 "$MISSING")
  echo "check one with: rucio replica list file --protocols root --rses $RSE --pfns $first"
  exit 1
fi
