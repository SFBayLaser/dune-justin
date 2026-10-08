#!/bin/bash
# Download the Cluster3D RecoCandidates outputs of one reco version (v01, v02, v03, ...) from rucio.
#
#   ./fetch_reco.sh VERSION [DIR] [FIRST] [LAST]
#
#   VERSION  v01, v02, v03 ... (the "Cluster3D_vNN" in the file name)
#   DIR      where the files go (default ./recontest_VERSION); files already in DIR or DIR/usertests are skipped
#   FIRST, LAST   spill numbers to fetch (default 1 to 250)
#
# Examples:
#   ./fetch_reco.sh v03 ./recontestv3             # everything v03 that is not on disk yet
#   ./fetch_reco.sh v01 ./recontest 229 229       # one spill
#   DRY_RUN=1 ./fetch_reco.sh v01 ./recontest     # only show what is missing, needs no rucio
#
# It skips what is already there, downloads the rest in chunks, and repeats up to 3 passes so a few
# transient failures do not need a manual rerun. Spills that are still missing afterwards are listed;
# those are probably not on the RSE at all (check one with the rucio replica list command printed).
# Set up rucio and a valid token/proxy first, in the same shell.
#
# Sharing: new files are created group-writable (umask 002), and at the end DIR is made readable by
# everyone (chmod -R a+rX). Set SHARE=0 to leave the permissions alone. Choose DIR on a disk the others
# can reach (for example under your area in /pnfs/dune/persistent/users or /exp/dune/data).

set -u
umask 0002
VER=${1:?usage: fetch_reco.sh VERSION [DIR] [FIRST] [LAST]}
DIR=${2:-./recontest_${VER}}
FIRST=${3:-1}
LAST=${4:-250}
RSE=${RSE:-DUNE_US_FNAL_DISK_STAGE}
SCOPE=usertests
PREFIX=MiniProdN5p3_NDComplex_FHC.spill.full.sanddrift
SUFFIX=EDEPSIM_SPILLS_TMSReco_Cluster3D_${VER}_RecoCandidates.root
CHUNK=${CHUNK:-20}

mkdir -p "$DIR"
MISSING="$DIR/files_missing_${VER}.txt"

list_missing() {
  : > "$MISSING"
  for i in $(seq "$FIRST" "$LAST"); do
    name=$(printf "%s.%07d.%s" "$PREFIX" "$i" "$SUFFIX")
    if [ ! -s "$DIR/$name" ] && [ ! -s "$DIR/$SCOPE/$name" ]; then
      echo "$SCOPE:$name" >> "$MISSING"
    fi
  done
  wc -l < "$MISSING"
}

n=$(list_missing)
echo "$VER: $n of $((LAST - FIRST + 1)) files are not in $DIR"
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
