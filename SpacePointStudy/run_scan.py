#!/usr/bin/env python3
"""Parameter scan of the space point builder using the second-pass fhicl (builder + Supera only).

Usage:  SpacePointStudy/run_scan.py scan_points_fd.json [--compare-only] [--tol 1 2 4]

The JSON spec:
  {"detector": {"fcl_dir": ..., "fcl_new": ..., "fcl_baseline": ...},
   "input": "<existing *_supera.root with gaushit, mcreco, sed...>", "events": 40, "outdir": ".../scan",
   "common": {"MaxHitChiSquare": 10.0},          # applied to every point (Hit3DBuilderAlg.<name>)
   "points": {"name": {"builder": "new"|"baseline", "params": {"DeltaPeakTimeSig": 1.75}}, ...}}

Each point writes <outdir>/<name>/{larcv.root,run.log,time.log,point.fcl}; finished points are skipped.
Everything runs in the SL7 container (bind of /media/usher/Drive2 is needed for the local dunereco build).
After the runs the truth comparison (compare_truth.py) is run on all points and written to
<outdir>/compare.txt and <outdir>/compare.json.
"""
import argparse, json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DRIVE = "/run/media/usher/Drive2"
R = f"{DRIVE}/DUNE"
SIF = str(Path.home() / "test/fnal-dev-sl7.sif")
HERE = Path(__file__).resolve().parent


def container(script, cwd="/tmp"):
    cmd = ["apptainer", "exec", "-B", f"/cvmfs,{DRIVE},{DRIVE}:/media/usher/Drive2", "--ipc", "--pid",
           SIF, "bash", "-c", script]
    return subprocess.run(cmd, cwd=cwd).returncode


def finished(d):
    """a point is done only if lar exited cleanly (larcv.root is created at job start)"""
    t = d / "time.log"
    return (d / "larcv.root").exists() and t.exists() and "Exit status: 0" in t.read_text()


def fval(v):
    return str(v).lower() if isinstance(v, bool) else str(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--compare-only", action="store_true")
    ap.add_argument("--tol", type=int, nargs="+", default=[1, 2, 4])
    ap.add_argument("--jobs", type=int, default=6, help="points run in parallel (each ~1.5 GB, 1 core)")
    a = ap.parse_args()
    spec = json.load(open(a.spec))
    out = Path(spec["outdir"])
    det = spec["detector"]
    fcl_dir = Path(det["fcl_dir"])
    nev = spec.get("events", 40)
    todo = []
    for name, p in spec["points"].items():
        d = out / name
        d.mkdir(parents=True, exist_ok=True)
        params = dict(spec.get("common", {})); params.update(p.get("params", {}))
        top = det["fcl_baseline"] if p["builder"] == "baseline" else det["fcl_new"]
        lines = [f'#include "{top}"'] + [
            f"physics.producers.cluster3d.Hit3DBuilderAlg.{k}: {fval(v)}" for k, v in params.items()]
        (d / "point.fcl").write_text("\n".join(lines) + "\n")
        if not finished(d):
            todo.append(name)
    print("to run:", todo or "nothing", flush=True)

    if todo and not a.compare_only:
        def run_point(n):
            rc = container(f"""
source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh > /dev/null 2>&1
cd {R}/FD/v10_24_00d00
source ./localProducts_larsoft_v10_24_00_e26_prof/setup > /dev/null 2>&1
setup dunesw v10_24_00d00 -q e26:prof > /dev/null 2>&1
cd {out}/{n}; echo "start {n} $(date +%T)"
FHICL_FILE_PATH={out}/{n}:{fcl_dir}:$FHICL_FILE_PATH /usr/bin/time -v lar -c point.fcl -s {spec["input"]} -n {nev} > run.log 2> time.log
echo "rc=$? end {n} $(date +%T)"
""")
            return n, rc
        with ThreadPoolExecutor(max_workers=a.jobs) as ex:
            for n, rc in ex.map(run_point, todo):
                print(f"{n}: container rc {rc}", flush=True)

    done = [n for n in spec["points"] if finished(out / n)]
    args = " ".join(f"{n}={out}/{n}/larcv.root" for n in done)
    container(f"""
source {HERE}/larcv_env.sh
python3 {HERE}/compare_truth.py {args} --tol {' '.join(map(str, a.tol))} --json {out}/compare.json 2>&1 \
  | grep -v '^Error in\\|FileEntry\\|autoload\\|^$' | tee {out}/compare.txt
""")
    # per-point timing
    for n in done:
        t = out / n / "time.log"
        if t.exists():
            for l in t.read_text().splitlines():
                if l.startswith("reco:cluster3d") or "Elapsed (wall" in l:
                    print(f"  {n:<22}{l.strip()[:110]}")


if __name__ == "__main__":
    sys.exit(main())
