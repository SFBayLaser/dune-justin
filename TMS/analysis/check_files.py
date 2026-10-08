# Integrity check of the downloaded justIN outputs: every file must open, have all trees with entries, and not be a
# recovered/truncated file. Writes files_ok.txt (sorted) and prints what is missing or bad.
# Usage (after sourcing the dune-tms setup.sh): python3 check_files.py <dir> <outdir>   (<dir> is searched recursively)
import ROOT, sys, glob, os, re
ROOT.gROOT.SetBatch(True)
d, out = sys.argv[1], sys.argv[2]
need = ["Reco_Tree", "Reco_Tree_C3D", "Truth_Info", "Truth_Info_C3D", "Truth_Spill", "Metadata", "Line_Candidates"]
ok, bad, seen = [], [], set()
for path in sorted(glob.glob(os.path.join(d, "**", "*_RecoCandidates.root"), recursive=True)):
    n = int(re.search(r"sanddrift\.(\d+)\.", path).group(1)); seen.add(n)
    f = ROOT.TFile.Open(path)
    if not f or f.IsZombie() or f.TestBit(ROOT.TFile.kRecovered):
        bad.append((n, "zombie/recovered")); continue
    counts = {}
    for t in need:
        tree = f.Get(t)
        counts[t] = tree.GetEntries() if tree else -1
    if any(counts[t] < 0 for t in need) or counts["Reco_Tree"] != counts["Reco_Tree_C3D"] or counts["Reco_Tree"] != counts["Truth_Info"]:
        bad.append((n, str(counts))); continue
    ok.append(path); f.Close()
open(os.path.join(out, "files_ok.txt"), "w").write("\n".join(ok) + "\n")
missing = [n for n in range(1, 251) if n not in seen]
print(f"{len(ok)} files OK, {len(bad)} bad, {len(missing)} of 1-250 not present")
for n, why in bad: print("  BAD", n, why)
print("  missing:", " ".join(f"{n:03d}" for n in missing))
