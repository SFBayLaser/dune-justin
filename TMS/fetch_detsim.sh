#!/bin/bash
# Download the stage-1 outputs (RecoCandidates + Readout) of one detector-simulation mode from rucio.
#
#   ./fetch_detsim.sh MODE [DIR] [FIRST] [LAST]
#
#   MODE   legacy | new | timing_thr1 | timing_thr3 (the "DetSim_<MODE>_v01" in the file names; VERSION=v02 for another version)
#   DIR    where the files go (default ./detsim_MODE); files already in DIR are skipped
#   FIRST, LAST   spill numbers to fetch (default 1 to 250)
#
# Besides the downloaded files, DIR gets symbolic links <NNNNNNN>_RecoCandidates.root / <NNNNNNN>_Readout.root, the layout
# scripts/Validation/DetSim/detsim_validation.py reads (one run directory per mode).
#   DRY_RUN=1 ./fetch_detsim.sh new ./detsim_new     # only show what is missing, needs no rucio
# Same behavior as fetch_reco.sh (chunks, up to 3 passes, lists what is still missing). Stops when less than MIN_FREE_GB
# (default 10) is free on DIR's disk: the four modes together are large, check with `du -sh` after the first chunk.
# Set up rucio and a valid token/proxy first, in the same shell.
set -u
umask 0002
MODE=${1:?usage: fetch_detsim.sh MODE [DIR] [FIRST] [LAST]}
VER=${VERSION:-v01}
DIR=${2:-./detsim_${MODE}}
FIRST=${3:-1}
LAST=${4:-250}
RSE=${RSE:-DUNE_US_FNAL_DISK_STAGE}
SCOPE=usertests
PREFIX=MiniProdN5p3_NDComplex_FHC.spill.full.sanddrift
STEM=EDEPSIM_SPILLS_DetSim_${MODE}_${VER}
CHUNK=${CHUNK:-10}
MIN_FREE_GB=${MIN_FREE_GB:-10}
mkdir -p "$DIR"
MISSING="$DIR/files_missing_${MODE}.txt"

list_missing() {
  : > "$MISSING"
  for i in $(seq "$FIRST" "$LAST"); do
    for kind in RecoCandidates Readout; do
      name=$(printf "%s.%07d.%s_%s.root" "$PREFIX" "$i" "$STEM" "$kind")
      [ -s "$DIR/$name" ] || echo "$SCOPE:$name" >> "$MISSING"
    done
  done
  wc -l < "$MISSING"
}
n=$(list_missing)
echo "$MODE: $n files are not in $DIR"
[ "$n" -eq 0 ] && exit 0
[ -n "${DRY_RUN:-}" ] && { echo "dry run; list written to $MISSING"; exit 0; }
command -v rucio > /dev/null || { echo "rucio not found: set it up first (and a valid token or proxy)"; exit 2; }

for pass in 1 2 3; do
  echo "pass $pass: downloading $n files from $RSE"
  while read -r -a chunk < <(head -n "$CHUNK" "$MISSING") && [ "${#chunk[@]}" -gt 0 ]; do
    free=$(df -BG --output=avail "$DIR" | tail -1 | tr -dc 0-9)
    [ "$free" -lt "$MIN_FREE_GB" ] && { echo "only ${free} GB free on $DIR: stopping"; exit 3; }
    rucio download --dir "$DIR" --no-subdir --rses "$RSE" "${chunk[@]}" || break
    n=$(list_missing); [ "$n" -eq 0 ] && break
  done
  n=$(list_missing); [ "$n" -eq 0 ] && break
done

for i in $(seq "$FIRST" "$LAST"); do
  for kind in RecoCandidates Readout; do
    name=$(printf "%s.%07d.%s_%s.root" "$PREFIX" "$i" "$STEM" "$kind")
    [ -s "$DIR/$name" ] && ln -sf "$name" "$DIR/$(printf '%07d_%s.root' "$i" "$kind")"
  done
done
[ "${SHARE:-1}" = "1" ] && chmod -R a+rX "$DIR" 2> /dev/null
if [ "$n" -eq 0 ]; then echo "$MODE: all files are in $DIR"; else
  echo "$MODE: $n files are still missing, listed in $MISSING"; exit 1; fi
