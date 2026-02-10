#!/usr/bin/env python3
import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

try:
    import yaml  # PyYAML
except ImportError:
    yaml = None


def load_config(path: Path) -> dict:
    text = path.read_text()
    if path.suffix.lower() in (".yaml", ".yml"):
        if yaml is None:
            raise RuntimeError(
                "PyYAML is not installed, but config is YAML. "
                "Install it (e.g. pip install pyyaml) or use JSON."
            )
        return yaml.safe_load(text)
    elif path.suffix.lower() == ".json":
        return json.loads(text)
    else:
        # Try YAML then JSON
        if yaml is not None:
            try:
                return yaml.safe_load(text)
            except Exception:
                pass
        return json.loads(text)


def require(cond: bool, msg: str):
    if not cond:
        raise ValueError(msg)


def as_str(v) -> str:
    if v is None:
        return ""
    return str(v)


def build_justin_cmd(argv_list, with_dune_setup: bool) -> list[str]:
    """
    If with_dune_setup is True, run through:
      bash -lc 'source ...; setup justin; <justin ...>'
    Otherwise run justin directly.
    """
    if not with_dune_setup:
        return argv_list

    # Note: 'setup justin' is a bash function from UPS after sourcing setup_dune.sh.
    prelude = (
        "source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh >/dev/null 2>&1; "
        "setup justin >/dev/null 2>&1; "
    )
    cmd_str = prelude + " ".join(shlex.quote(x) for x in argv_list)
    return ["bash", "-lc", cmd_str]


def run_cmd(argv_list, dry_run: bool, with_dune_setup: bool, capture: bool = False) -> subprocess.CompletedProcess:
    real_argv = build_justin_cmd(argv_list, with_dune_setup)
    printable = " ".join(shlex.quote(x) for x in real_argv)
    print(f"+ {printable}")

    if dry_run:
        # Fake successful run
        class Dummy:
            returncode = 0
            stdout = ""
            stderr = ""
        return Dummy()  # type: ignore

    return subprocess.run(
        real_argv,
        check=False,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def merge_defaults(stage: dict, defaults: dict) -> dict:
    merged = dict(defaults)
    merged.update(stage)  # stage overrides defaults
    # env should merge dicts (defaults.env + stage.env)
    env_d = dict(defaults.get("env", {}) or {})
    env_s = dict(stage.get("env", {}) or {})
    env_d.update(env_s)
    merged["env"] = env_d
    return merged


def main():
    ap = argparse.ArgumentParser(description="Submit a justIN v1.06 workflow from YAML/JSON config.")
    ap.add_argument("--config", required=True, help="Path to workflow YAML/JSON file")
    ap.add_argument("--dry-run", action="store_true", help="Print justin commands without executing")
    ap.add_argument("--with-dune-setup", action="store_true",
                    help="Run each justin command under 'source setup_dune.sh; setup justin' (bash -lc)")
    ap.add_argument("--instance", default=None, help="Optional: pass --instance to justin")
    ap.add_argument("--url", default=None, help="Optional: pass --url to justin")
    ap.add_argument("--verbose", action="store_true", help="Pass -v to justin")
    args = ap.parse_args()

    cfg_path = Path(args.config).expanduser().resolve()
    cfg = load_config(cfg_path)

    workflow = cfg.get("workflow", {}) or {}
    defaults = cfg.get("defaults", {}) or {}
    stages = cfg.get("stages", []) or []

    require(isinstance(stages, list) and len(stages) > 0, "Config must contain a non-empty 'stages:' list.")
    require("description" in workflow, "workflow.description is required")
    require("monte_carlo" in workflow, "workflow.monte_carlo is required")

    # Global justin flags (optional)
    justin_global = ["justin"]
    if args.verbose:
        justin_global.append("-v")
    if args.instance:
        justin_global += ["--instance", args.instance]
    if args.url:
        justin_global += ["--url", args.url]

    # ---- create workflow ----
    create_wf = justin_global + [
        "create-workflow",
        "--description", as_str(workflow["description"]),
        "--monte-carlo", as_str(workflow["monte_carlo"]),
    ]
    cp = run_cmd(create_wf, dry_run=args.dry_run, with_dune_setup=args.with_dune_setup, capture=True)
    if getattr(cp, "returncode", 1) != 0:
        print("ERROR: create-workflow failed.", file=sys.stderr)
        if hasattr(cp, "stderr") and cp.stderr:
            print(cp.stderr, file=sys.stderr)
        sys.exit(2)

    wfid = (cp.stdout or "").strip() if not args.dry_run else "DRYRUN_WFID"
    require(wfid != "", "Could not parse workflow id from create-workflow output.")
    print(f"WFID={wfid}")

    # ---- create stages ----
    for st in stages:
        require(isinstance(st, dict), "Each stage entry must be a mapping/dict.")
        require("id" in st, "Each stage needs an 'id'.")
        st_merged = merge_defaults(st, defaults)

        stage_id = as_str(st_merged["id"])
        repo = st_merged.get("repo", defaults.get("repo"))
        ref = st_merged.get("ref", defaults.get("ref"))
        jobscript = st_merged.get("jobscript")

        require(repo, f"Stage {stage_id}: repo missing (set defaults.repo or stage.repo).")
        require(ref, f"Stage {stage_id}: ref missing (set defaults.ref or stage.ref).")
        require(jobscript, f"Stage {stage_id}: jobscript missing.")

        cmd = justin_global + [
            "create-stage",
            "--workflow-id", as_str(wfid),
            "--stage-id", stage_id,
            "--jobscript-git", f"{repo}/{jobscript}:{ref}",
        ]

        # Resources
        if "wall_seconds" in st_merged:
            cmd += ["--wall-seconds", as_str(st_merged["wall_seconds"])]
        if "rss_mib" in st_merged:
            cmd += ["--rss-mib", as_str(st_merged["rss_mib"])]
        if "processors" in st_merged:
            cmd += ["--processors", as_str(st_merged["processors"])]
        if st_merged.get("gpu", False):
            cmd += ["--gpu"]

        # Env vars (repeatable)
        env = st_merged.get("env", {}) or {}
        require(isinstance(env, dict), f"Stage {stage_id}: env must be a dict of KEY: VALUE")
        for k, v in env.items():
            cmd += ["--env", f"{k}={v}"]

        # code version to run (optional; can override defaults)
        if "tarfile_dir" in st_merged and st_merged["tarfile_dir"] is not None:
            cmd += ["--env", "INPUT_TAR_DIR_LOCAL="+as_str(st_merged["tarfile_dir"])]

        # code version to run (optional; can override defaults)
        if "dunesw_version" in st_merged and st_merged["dunesw_version"] is not None:
            cmd += ["--env", "DUNESW_VERSION="+as_str(st_merged["dunesw_version"])]
        else:
            cmd += "--env DUNESW_VERSION=v10_17_01d00"

        # Path to FHICL files to pull over
        if "fhicl_files" in st_merged and st_merged["fhicl_files"] is not None:
            cmd += ["--env", "FCL_TGZ_URL="+as_str(st_merged["fhicl_files"])]

        # Output patterns (repeatable)
        # - final stage typically uses output_patterns (list) or output_pattern (string)
        # - intermediate stage uses output_pattern_next_stage (string)
        if "output_pattern_next_stage" in st_merged and st_merged["output_pattern_next_stage"]:
            cmd += ["--output-pattern-next-stage", as_str(st_merged["output_pattern_next_stage"])]

        # Accept either:
        #   output_patterns: [..]
        # or output_pattern: ".."  (single)
        # or your existing "output_patterns" for multiple
        if "output_patterns" in st_merged and st_merged["output_patterns"]:
            ops = st_merged["output_patterns"]
            require(isinstance(ops, list), f"Stage {stage_id}: output_patterns must be a list")
            for pat in ops:
                cmd += ["--output-pattern", as_str(pat)]
        elif "output_pattern" in st_merged and st_merged["output_pattern"]:
            cmd += ["--output-pattern", as_str(st_merged["output_pattern"])]

        # RSE targeting (optional)
        if st_merged.get("output_rse"):
            cmd += ["--output-rse", as_str(st_merged["output_rse"])]
        if st_merged.get("output_rse_expression"):
            cmd += ["--output-rse-expression", as_str(st_merged["output_rse_expression"])]

        # Lifetime (optional; can override defaults)
        if "lifetime_days" in st_merged and st_merged["lifetime_days"] is not None:
            cmd += ["--lifetime-days", as_str(st_merged["lifetime_days"])]

        # max-distance (optional; can override defaults)
        if "max_distance" in st_merged and st_merged["max_distance"] is not None:
            cmd += ["--max-distance", as_str(st_merged["max_distance"])]

        # Site restrictions (repeatable --site)
        # (This influences what you saw as Desired_Sites in classads)
        if st_merged.get("sites"):
            sites = st_merged["sites"]
            require(isinstance(sites, list), f"Stage {stage_id}: sites must be a list")
            for s in sites:
                cmd += ["--site", as_str(s)]

        # Extra classads (optional)
        if st_merged.get("classad"):
            # allow either a single string or list of strings
            ca = st_merged["classad"]
            if isinstance(ca, list):
                for one in ca:
                    cmd += ["--classad", as_str(one)]
            else:
                cmd += ["--classad", as_str(ca)]

        cp = run_cmd(cmd, dry_run=args.dry_run, with_dune_setup=args.with_dune_setup, capture=True)
        if getattr(cp, "returncode", 1) != 0:
            print(f"ERROR: create-stage failed for stage {stage_id}.", file=sys.stderr)
            if hasattr(cp, "stderr") and cp.stderr:
                print(cp.stderr, file=sys.stderr)
            sys.exit(3)

    # ---- submit workflow ----
    submit = justin_global + ["submit-workflow", "--workflow-id", as_str(wfid)]
    cp = run_cmd(submit, dry_run=args.dry_run, with_dune_setup=args.with_dune_setup, capture=True)
    if getattr(cp, "returncode", 1) != 0:
        print("ERROR: submit-workflow failed.", file=sys.stderr)
        if hasattr(cp, "stderr") and cp.stderr:
            print(cp.stderr, file=sys.stderr)
        sys.exit(4)

    print(f"Submitted WFID={wfid}")

    # ---- optional: show-stages ----
    show = justin_global + ["show-stages", "--workflow-id", as_str(wfid)]
    run_cmd(show, dry_run=args.dry_run, with_dune_setup=args.with_dune_setup, capture=False)


if __name__ == "__main__":
    main()
