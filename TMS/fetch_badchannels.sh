#!/bin/bash
# Download the validation outputs of the bad channel scan (tms_badchannels_make_configs.py + tms_validation[_nodraw].jobscript)
# from rucio: for each set and spill, the legacy and the Cluster3D Tracking_Validation file. Same behavior as fetch_validation.sh.
#
#   ./fetch_badchannels.sh VERSION [DIR] [FIRST] [LAST]
#
#   VERSION  v01 ... (the version given to tms_badchannels_make_configs.py)
#   DIR      where the files go (default ./badchannels_VERSION); files already in DIR or DIR/usertests are skipped
#   FIRST, LAST   spill numbers to fetch (default 1 to 250)
#
#   SETS="f00 f05_s1 ..."   only these sets (default: f00 and f05, f10, f15, f20, f25 for seeds 1 to 3)
#   DRY_RUN=1               only show what is missing, needs no rucio
#   WITH_LOG=1              also fetch the *_validation.log files
#   RSE=any                 take any replica (default: only DUNE_US_FNAL_DISK_STAGE); RSE=<name> for one other storage element
#   PROTOCOL=root           force a transfer protocol (rucio chooses davs for some storage elements, which needs a proxy)
#   CHUNK, SHARE            as in fetch_validation.sh
#
# Jobs that crashed have no output, so a few files per set stay missing after the three passes: they are listed in
# DIR/files_missing_badchannels_VERSION.txt, and the exit status is 1. That list is the spills badchannel_scan.py will leave out.
# Set up rucio and a valid token/proxy first, in the same shell. Then:  badchannel_scan.py DIR OUT --version VERSION

set -u
umask 0002
VER=${1:?usage: fetch_badchannels.sh VERSION [DIR] [FIRST] [LAST]}
VER=${VER,,}
DIR=${2:-./badchannels_${VER}}
FIRST=${3:-1}
LAST=${4:-250}
RSE=${RSE-DUNE_US_FNAL_DISK_STAGE}   # RSE=any (or empty): take any replica, not only this storage element
[ "$RSE" = "any" ] && RSE=
SCOPE=usertests
PREFIX=MiniProdN5p3_NDComplex_FHC.spill.full.sanddrift
SETS=${SETS:-"f00 $(for s in 1 2 3; do for f in 05 10 15 20 25; do printf 'f%s_s%s ' $f $s; done; done)"}
KINDS="legacy cluster3d"
CHUNK=${CHUNK:-20}

mkdir -p "$DIR"
MISSING="$DIR/files_missing_badchannels_${VER}.txt"

list_missing() {
  : > "$MISSING"
  for set in $SETS; do
    stem=EDEPSIM_SPILLS_TMSReco_BadCh_${set}_${VER}_RecoCandidates
    suffixes=""
    for kind in $KINDS; do suffixes="$suffixes ${stem}_validation_${kind}.root"; done
    [ -n "${WITH_LOG:-}" ] && suffixes="$suffixes ${stem}_validation.log"
    for i in $(seq "$FIRST" "$LAST"); do
      for suffix in $suffixes; do
        name=$(printf "%s.%07d.%s" "$PREFIX" "$i" "$suffix")
        if [ ! -s "$DIR/$name" ] && [ ! -s "$DIR/$SCOPE/$name" ]; then
          echo "$SCOPE:$name" >> "$MISSING"
        fi
      done
    done
  done
  wc -l < "$MISSING"
}

nsets=$(echo $SETS | wc -w)
total=$(( nsets * (LAST - FIRST + 1) * 2 ))
n=$(list_missing)
echo "$VER: $n of $total files ($nsets sets) are not in $DIR"
[ "$n" -eq 0 ] && exit 0
if [ -n "${DRY_RUN:-}" ]; then
  echo "dry run; list written to $MISSING"
  exit 0
fi
command -v rucio > /dev/null || { echo "rucio not found: set it up first (and a valid token or proxy)"; exit 2; }

for pass in 1 2 3; do
  echo "pass $pass: downloading $n files from ${RSE:-any RSE}"
  xargs -n "$CHUNK" rucio download --dir "$DIR" --no-subdir ${RSE:+--rses "$RSE"} ${PROTOCOL:+--protocol "$PROTOCOL"} < "$MISSING"
  n=$(list_missing)
  [ "$n" -eq 0 ] && break
done

[ "${SHARE:-1}" = "1" ] && chmod -R a+rX "$DIR" 2> /dev/null

if [ "$n" -eq 0 ]; then
  echo "$VER: all files are in $DIR"
else
  echo "$VER: $n files are still missing (jobs that crashed have no output), listed in $MISSING"
  echo "per set:"; sed -E 's/.*BadCh_(f[0-9]+(_s[0-9]+)?)_.*/  \1/' "$MISSING" | sort | uniq -c
  first=$(head -1 "$MISSING")
  echo "check one with: rucio list-file-replicas $first   (shows every storage element that has it; then RSE=<that one> or RSE=any)"
  exit 1
fi
