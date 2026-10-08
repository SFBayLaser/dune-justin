#!/bin/bash
# Merge the per-file outputs of the justIN validation stage (tms_validation.jobscript) into one legacy and one
# Cluster3D validation file, for comparing the two reconstructions.
#
# Usage: bash merge_validation.sh <directory with the downloaded files> [output directory (default: that directory)]
#
# Looks, recursively, for  *_validation_legacy.root  and  *_validation_cluster3d.root.  Needs ROOT's hadd on the PATH
# (for example after sourcing the dune-tms setup.sh). Writes <output>/legacy.root and <output>/cluster3d.root.
#
# Only files that were produced from the same stage 1 output are merged into both sets, so the two files cover exactly
# the same events: a file with a legacy output but no Cluster3D output (or the reverse) is listed and left out of both.
# hadd adds histograms bin by bin, which is correct for the counts and the numerator/denominator histograms, but not
# for anything computed per file (ratios, fitted widths): recompute those from the merged file.

indir="${1:?usage: merge_validation.sh <input directory> [output directory]}"
outdir="${2:-$indir}"
mkdir -p "$outdir" || exit 1
command -v hadd > /dev/null || { echo "ERROR: hadd not found; set up ROOT first" >&2; exit 2; }

# Name of the stage 1 file a validation output came from: the file name without the _validation_<kind>.root suffix.
stem() { basename "$1" | sed -E 's/_validation_(legacy|cluster3d)\.root$//'; }

legacy=(); c3d=(); skipped=0
while IFS= read -r f; do
  s=$(stem "$f")
  mate=$(find "$indir" -name "${s}_validation_cluster3d.root" -size +0 | head -1)
  if [[ -s "$f" && -n "$mate" ]]; then
    legacy+=("$f"); c3d+=("$mate")
  else
    echo "Left out (no matching non-empty Cluster3D file): $f"; skipped=$((skipped+1))
  fi
done < <(find "$indir" -name '*_validation_legacy.root' -size +0 | sort)

# Cluster3D outputs with no legacy mate
while IFS= read -r f; do
  s=$(stem "$f")
  [[ -n $(find "$indir" -name "${s}_validation_legacy.root" -size +0 | head -1) ]] || { echo "Left out (no matching legacy file): $f"; skipped=$((skipped+1)); }
done < <(find "$indir" -name '*_validation_cluster3d.root' -size +0 | sort)

n=${#legacy[@]}
echo "Merging $n files ($skipped left out)"
(( n > 0 )) || { echo "ERROR: nothing to merge under $indir" >&2; exit 3; }

hadd -f -n 200 "$outdir/legacy.root"    "${legacy[@]}" > "$outdir/hadd_legacy.log"    2>&1 || { echo "ERROR: hadd failed for legacy, see $outdir/hadd_legacy.log" >&2; exit 4; }
hadd -f -n 200 "$outdir/cluster3d.root" "${c3d[@]}"    > "$outdir/hadd_cluster3d.log" 2>&1 || { echo "ERROR: hadd failed for Cluster3D, see $outdir/hadd_cluster3d.log" >&2; exit 4; }

# One input file name per line, in the order merged, for later steps that read the original files
printf '%s\n' "${legacy[@]}" > "$outdir/merged_legacy_files.txt"
echo "Wrote $outdir/legacy.root and $outdir/cluster3d.root from $n files"
ls -lh "$outdir/legacy.root" "$outdir/cluster3d.root"
