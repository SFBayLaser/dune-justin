#!/bin/bash
# Reco-level analysis of one justIN production: integrity check of the RecoCandidates files, then the endpoint dz, cross
# table, page data, range Gaussian fits and the scorecard. Writes small JSON/npy files to bring back from the gpvm.
#
#   ./run_analysis.sh RECO_DIR VALIDATION_DIR OUT_DIR
#
#   RECO_DIR        directory with the *_RecoCandidates.root files (searched recursively, so usertests/ is fine)
#   VALIDATION_DIR  directory with legacy.root and cluster3d.root from merge_validation.sh. If merged_legacy_files.txt is
#                   there too, only those spills are analyzed, so the dz/scorecard numbers and the validation
#                   histograms describe the same files. Otherwise every file that passes the check is used.
#   OUT_DIR         everything is written here (created if needed)
#
# Needs the dune-tms environment (source setup.sh inside dune-tms) so PyROOT and numpy are available.
# (page_data.json calls the Cluster3D tracker "linked": that is the key the comparison-page template reads.)
# Outputs: files_ok.txt, files.txt (the list used), endpoint_dz.log, dz_legacy.npy, dz_cluster3d.npy, cross_table.json,
#          page_data.json, fits.json, scorecard.json, and a *.log for each step.

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECO=${1:?usage: run_analysis.sh RECO_DIR VALIDATION_DIR OUT_DIR}
VAL=${2:?usage: run_analysis.sh RECO_DIR VALIDATION_DIR OUT_DIR}
OUT=${3:?usage: run_analysis.sh RECO_DIR VALIDATION_DIR OUT_DIR}
mkdir -p "$OUT" || exit 1
python3 -c "import ROOT, numpy" 2>/dev/null || { echo "ERROR: PyROOT/numpy not available; source setup.sh in dune-tms first" >&2; exit 2; }
for f in legacy.root cluster3d.root; do [[ -s "$VAL/$f" ]] || { echo "ERROR: $VAL/$f not found" >&2; exit 3; }; done

step() {  # step NAME COMMAND...: run, log to OUT/NAME.log, stop on failure
  name=$1; shift
  echo "== $name"
  "$@" > "$OUT/$name.log" 2>&1 || { echo "ERROR: $name failed, see $OUT/$name.log" >&2; exit 4; }
}

step check_files python3 "$here/check_files.py" "$RECO" "$OUT"
grep -v "^Info" "$OUT/check_files.log" | head -5

# The list to analyze: the files that passed the check, restricted to the validated spills if that list exists.
if [[ -s "$VAL/merged_legacy_files.txt" ]]; then
  sed -E 's#.*/##; s#_validation_legacy\.root$##' "$VAL/merged_legacy_files.txt" | sort > "$OUT/merged_stems.txt"
  while IFS= read -r f; do
    grep -qxF "$(basename "$f" .root)" "$OUT/merged_stems.txt" && echo "$f"
  done < "$OUT/files_ok.txt" > "$OUT/files.txt"
else
  cp "$OUT/files_ok.txt" "$OUT/files.txt"
fi
n=$(wc -l < "$OUT/files.txt")
echo "analyzing $n files"
(( n > 0 )) || { echo "ERROR: no files to analyze" >&2; exit 5; }

step endpoint_dz  python3 "$here/endpoint_dz.py" "$OUT/files.txt" "$OUT"
step cross_table  python3 "$here/cross_table.py" "$OUT/files.txt" "$OUT/cross_table.json"
step page_data    python3 "$here/extract_page_data.py" "$OUT/page_data.json" \
                    legacy="$VAL/legacy.root:$OUT/dz_legacy.npy" linked="$VAL/cluster3d.root:$OUT/dz_cluster3d.npy"
step range_fit    python3 "$here/range_gaus_fit.py" "$OUT/files.txt" "$OUT/fits.json"
step scorecard    python3 "$here/scorecard.py" "$OUT/files.txt" "$OUT/scorecard.json"
echo "done: results in $OUT"
