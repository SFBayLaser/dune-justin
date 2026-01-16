#
# This script sets up the workflow to run gen->g4->detsim->reco for larcv output 
# You can execute with this:
#   bash -lc "source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh; setup justin; python3 workflow.py"
#
#!/usr/bin/env python3
import os
import shlex
import subprocess
import sys
from typing import List


def run(cmd: List[str], *, capture: bool = True, check: bool = True) -> str:
    """Run a command, echo it, and return stdout."""
    print("+", " ".join(shlex.quote(c) for c in cmd), flush=True)
    res = subprocess.run(
        cmd,
        text=True,
        capture_output=capture,
        check=False,
        env=os.environ,
    )
    if capture:
        if res.stdout:
            print(res.stdout, end="")
        if res.stderr:
            # keep stderr visible but not fatal unless check=True
            print(res.stderr, end="", file=sys.stderr)

    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed (rc={res.returncode}): {' '.join(cmd)}")
    return (res.stdout or "").strip()


def main() -> int:
    # ---- user knobs ----
    NFILESTOGEN = 5
    NEVENTS     = 50

    REPO_FOLDER = "testing/multistep"
    REPO        = "SFBayLaser/dune-justin"
    REPO_BRANCH = "main"

    GEN_OUT    = "*_gen.root"
    G4_OUT     = "*_g4.root"
    DETSIM_OUT = "*_detsim.root"
    RECO_OUT   = "*_reco.root"
    LARCV_OUT  = "*_larcv.root"

    GEN_FHICL_FILE    = "mpvmpr_gen_1x2x6.fcl"
    G4_FHICL_FILE     = "standard_g4_dune10kt_1x2x6.fcl"
    DETSIM_FHICL_FILE = "standard_detsim_dune10kt_1x2x6.fcl"
    RECO_FHICL_FILE   = "standard_mythical_supera_dune10kt_1x2x6.fcl"

    GEN_WALL_TIME    = 14400
    GEN_RSS_MEM      = 4000
    G4_WALL_TIME     = 28800
    G4_RSS_MEM       = 6000
    DETSIM_WALL_TIME = 28800
    DETSIM_RSS_MEM   = 6000
    RECO_WALL_TIME   = 28800
    RECO_RSS_MEM     = 6000

    # IMPORTANT:
    # This Python script assumes you already have the DUNE/justin environment set up
    # in your shell (source setup_dune.sh; setup justin) BEFORE running it.
    #
    # If you want the script to do that itself, run it like:
    #   bash -lc "source .../setup_dune.sh; setup justin; python3 workflow.py"
    #

    # ---- create workflow ----
    wfid = run([
        "justin", "create-workflow",
        "--description", "gen->reco 2 hit",
        "--monte-carlo", str(NFILESTOGEN),
    ])

    # Some justin versions print extra text; keep only the first token that looks like an int
    wfid_token = wfid.split()[0]
    if not wfid_token.isdigit():
        raise RuntimeError(f"Couldn't parse workflow id from output: {wfid!r}")
    WFID = wfid_token
    print(f"WFID={WFID}")

    # ---- stage 1: GEN ----
    run([
        "justin", "create-stage",
        "--workflow-id", WFID,
        "--stage-id", "1",
        "--jobscript-git", f"{REPO}/{REPO_FOLDER}/gen.jobscript:{REPO_BRANCH}",
        "--wall-seconds", GEN_WALL_TIME,
        "--rss-mib", GEN_RSS_MEM,
        "--env", f"NEVENTS={NEVENTS}",
        "--env", f"JOB_FHICL_FILE={GEN_FHICL_FILE}",
        "--output-pattern-next-stage", GEN_OUT,
        "--lifetime-days", "1",
    ])

    # ---- stage 2: G4 ----
    run([
        "justin", "create-stage",
        "--workflow-id", WFID,
        "--stage-id", "2",
        "--jobscript-git", f"{REPO}/{REPO_FOLDER}/g4.jobscript:{REPO_BRANCH}",
        "--env", f"JOB_FHICL_FILE={G4_FHICL_FILE}",
        "--wall-seconds", G4_WALL_TIME,
        "--rss-mib", G4_RSS_MEM,
        "--output-pattern-next-stage", G4_OUT,
        "--lifetime-days", "1",
    ])

    # ---- stage 3: DETSIM ----
    run([
        "justin", "create-stage",
        "--workflow-id", WFID,
        "--stage-id", "3",
        "--jobscript-git", f"{REPO}/{REPO_FOLDER}/detsim.jobscript:{REPO_BRANCH}",
        "--env", f"JOB_FHICL_FILE={DETSIM_FHICL_FILE}",
        "--wall-seconds", DETSIM_WALL_TIME,
        "--rss-mib", DETSIM_RSS_MEM,
        "--output-pattern-next-stage", DETSIM_OUT,
        "--lifetime-days", "1",
    ])

    # ---- stage 4: RECO ----
    run([
        "justin", "create-stage",
        "--workflow-id", WFID,
        "--stage-id", "4",
        "--jobscript-git", f"{REPO}/{REPO_FOLDER}/reco.jobscript:{REPO_BRANCH}",
        "--env", "JOB_FHICL_FILE="+RECO_FHICL_FILE,
        "--wall-seconds", RECO_WALL_TIME,
        "--rss-mib", RECO_RSS_MEM,
        "--output-pattern", RECO_OUT,
        "--output-pattern", LARCV_OUT,
        "--output-rse-expression", "DUNE_US_FNAL_DISK_STAGE",
        "--lifetime-days", "90",
    ])

    # ---- submit ----
    run(["justin", "submit-workflow", "--workflow-id", WFID])

    print(f"Submitted WFID={WFID}")

    # ---- monitor helpers ----
    run(["justin", "show-stages", "--workflow-id", WFID], check=False)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise SystemExit(2)
