#!/usr/bin/env python3
"""Parameter scan of the space point builder with hit-level (pre-Supera) truth matching.

Usage:  SpacePointStudy/run_hit_scan.py scan_hit_fd.json [--dep] [--no-hit] [--eval-only] [--tols 1 2 5] [--jobs 6] [--eval-events N]

Same JSON spec as run_scan.py, but the fcl names point at the reco-only stage (sp_hit_dune10kt_1x2x6[_baseline].fcl: builder only,
no Supera, writes a small sp_art.root with cluster3d + gaushit):
  {"detector": {"fcl_dir": ..., "fcl_new": "sp_hit_dune10kt_1x2x6.fcl", "fcl_baseline": "sp_hit_dune10kt_1x2x6_baseline.fcl"},
   "input": "<*_supera.root with gaushit and the SimChannels>", "events": 20, "outdir": ".../hitscan",
   "common": {"MaxHitChiSquare": 10.0}, "points": {"name": {"builder": "new"|"baseline", "params": {...}}}}
Each point writes <outdir>/<name>/{sp_art.root, run.log, time.log, point.fcl, hit_eval.json, hit_eval.txt}; finished points are skipped
(delete hit_eval.json to re-evaluate). Truth hit cache: <outdir>/truth_cache.pkl. Summary table: <outdir>/hit_table.txt.
"""
import argparse, json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DRIVE = "/run/media/usher/Drive2"
R = f"{DRIVE}/DUNE"
SIF = str(Path.home() / "test/fnal-dev-sl7.sif")
HERE = Path(__file__).resolve().parent


def container(script, cwd="/tmp"):
    cmd = ["apptainer", "exec", "-B", f"/cvmfs,{DRIVE},{DRIVE}:/media/usher/Drive2", "--ipc", "--pid", SIF, "bash", "-c", script]
    return subprocess.run(cmd, cwd=cwd).returncode


def reco_done(d):
    t = d / "time.log"
    return (d / "sp_art.root").exists() and t.exists() and "Exit status: 0" in t.read_text()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--eval-only", action="store_true")
    ap.add_argument("--tols", type=float, nargs="+", default=[1, 2, 5])
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--dep", action="store_true", help="also run the deposit-level evaluation (sp_truth_dep.py)")
    ap.add_argument("--no-hit", action="store_true", help="skip the older per-hit evaluation (sp_truth_scan.py)")
    ap.add_argument("--eval-events", type=int, default=0, help="evaluate only the first N events (0 = all)")
    a = ap.parse_args()
    spec = json.load(open(a.spec)); out = Path(spec["outdir"]); det = spec["detector"]; fcl_dir = Path(det["fcl_dir"])
    todo = []
    for name, p in spec["points"].items():
        d = out / name; d.mkdir(parents=True, exist_ok=True)
        params = dict(spec.get("common", {})); params.update(p.get("params", {}))
        top = det["fcl_baseline"] if p["builder"] == "baseline" else det["fcl_new"]
        fv = lambda v: str(v).lower() if isinstance(v, bool) else str(v)
        (d / "point.fcl").write_text("\n".join([f'#include "{top}"'] + [
            f"physics.producers.cluster3d.Hit3DBuilderAlg.{k}: {fv(v)}" for k, v in params.items()]) + "\n")
        if not reco_done(d): todo.append(name)
    print("reco to run:", todo or "nothing", flush=True)
    if todo and not a.eval_only:
        def run_point(n):
            return n, container(f"""
source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh > /dev/null 2>&1
cd {R}/FD/v10_24_00d00
source ./localProducts_larsoft_v10_24_00_e26_prof/setup > /dev/null 2>&1
setup dunesw v10_24_00d00 -q e26:prof > /dev/null 2>&1
cd {out}/{n}; rm -f hit_eval.json; echo "start {n} $(date +%T)"
FHICL_FILE_PATH={out}/{n}:{fcl_dir}:$FHICL_FILE_PATH /usr/bin/time -v lar -c point.fcl -s {spec["input"]} -n {spec.get("events", 20)} > run.log 2> time.log
echo "rc=$? end {n} $(date +%T)"
""")
        with ThreadPoolExecutor(max_workers=a.jobs) as ex:
            for n, rc in ex.map(run_point, todo): print(f"{n}: container rc {rc}", flush=True)

    ready_all = [n for n in spec["points"] if reco_done(out / n)]
    evaluators = [("sp_truth_scan.py", "hit_eval.json", "truth_cache.pkl", f"--tols {' '.join(map(str, a.tols))}", "hit_table.txt"),
                  ("sp_truth_dep.py", "dep_eval.json", "truth_ide_cache.pkl", "", "dep_table.txt")]
    for script, js, cname, extra, tname in evaluators:
        if script == "sp_truth_dep.py" and not a.dep: continue
        if script == "sp_truth_scan.py" and a.no_hit: continue
        ready = [n for n in ready_all if not (out / n / js).exists()]
        common = f"--sim-file {spec['input']} --cache {out / cname} --events {a.eval_events} {extra}"
        py = f"python3 {HERE}/{script}"
        if ready:
            print(f"evaluating ({script}):", ready, flush=True)
            # first point alone builds the truth cache, the others then run in parallel
            container(f"source {HERE}/gallery_env.sh; {py} {out}/{ready[0]} {common} 2>&1 | grep -v '^Error in\\|autoload'")
            rest = ready[1:]
            if rest:
                container(f"source {HERE}/gallery_env.sh; printf '%s\\n' {' '.join(rest)} | xargs -P {a.jobs} -I{{}} sh -c "
                          f"'{py} {out}/{{}} {common} > {out}/{{}}/{js}.log 2>&1'")
        names = [n for n in spec["points"] if (out / n / js).exists()]
        container(f"source {HERE}/gallery_env.sh; {py} --table {' '.join(str(out / n) for n in names)} | tee {out}/{tname}")


if __name__ == "__main__":
    sys.exit(main())
