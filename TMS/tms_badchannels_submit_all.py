#!/usr/bin/env python3
"""Submit every workflow config made by tms_badchannels_make_configs.py, one after the other.

For each config it runs MCJobSubmission/mcJobSubmission.py --config <file> (the same command you would type by
hand), reads the workflow id from its "Submitted WFID=<n>" line, and appends a line to a log, so a re-run skips
what is already submitted and a failed submission does not stop the others.

Usage (from dune-justin/TMS, in the shell where you submit by hand):
  tms_badchannels_submit_all.py [CONFIG_DIR] [--sets f00 f10_s1 ...] [--dry-run] [--yes]
                                [--with-dune-setup] [--delay SECONDS] [--log FILE]
  CONFIG_DIR   directory with tms_badchannels_<set>_config.json (default badchannels_configs)
  --sets       only these sets (default: every config in CONFIG_DIR)
  --dry-run    run mcJobSubmission.py --dry-run: prints the justin commands, submits nothing, logs nothing
  --yes        do not ask for confirmation (it asks otherwise, since each workflow is a full dataset)
  --delay      seconds to wait between submissions (default 5)
  --log        submission log (default CONFIG_DIR/submitted_workflows.tsv): set, workflow id, time, tag
The sets already in the log are skipped; remove their lines to submit them again.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SUBMIT = os.path.join(HERE, "..", "MCJobSubmission", "mcJobSubmission.py")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config_dir", nargs="?", default="badchannels_configs")
    ap.add_argument("--sets", nargs="+")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--with-dune-setup", action="store_true")
    ap.add_argument("--delay", type=float, default=5.0)
    ap.add_argument("--log")
    args = ap.parse_args()

    log = args.log or os.path.join(args.config_dir, "submitted_workflows.tsv")
    done = {}
    if os.path.exists(log):
        for line in open(log):
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2:
                done[parts[0]] = parts[1]

    todo = []
    for path in sorted(glob.glob(os.path.join(args.config_dir, "tms_badchannels_*_config.json"))):
        name = re.match(r"tms_badchannels_(.*)_config\.json", os.path.basename(path)).group(1)
        if args.sets and name not in args.sets:
            continue
        if name in done:
            print(f"skip {name}: already submitted as workflow {done[name]}")
            continue
        with open(path) as f:
            cfg = json.load(f)
        todo.append((name, path, cfg["workflow"]["mql"], cfg["stages"][0]["env"]["TMS_PRODUCTION_TAG"]))
    if args.sets:
        missing = set(args.sets) - {t[0] for t in todo} - set(done)
        if missing:
            sys.exit(f"no config for: {', '.join(sorted(missing))}")
    if not todo:
        print("nothing to submit")
        return

    print(f"{len(todo)} workflow(s) to submit:")
    for name, _, mql, tag in todo:
        print(f"  {name:10s} tag {tag}   {mql.replace('files from neardet-lar-tms-sand:', '')}")
    if not args.dry_run and not args.yes:
        if input("Submit these? [y/N] ").strip().lower() != "y":
            print("not submitted")
            return

    failed = []
    for i, (name, path, _, tag) in enumerate(todo):
        cmd = [sys.executable, SUBMIT, "--config", path]
        if args.dry_run:
            cmd.append("--dry-run")
        if args.with_dune_setup:
            cmd.append("--with-dune-setup")
        print(f"[{i + 1}/{len(todo)}] {name}: {' '.join(cmd)}")
        cp = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        print(cp.stdout.rstrip())
        match = re.search(r"Submitted WFID=(\S+)", cp.stdout)
        if args.dry_run:
            continue
        if cp.returncode != 0 or not match:
            print(f"FAILED: {name} (exit {cp.returncode}); not logged, will be retried on the next run")
            failed.append(name)
        else:
            with open(log, "a") as f:
                f.write(f"{name}\t{match.group(1)}\t{time.strftime('%Y-%m-%d %H:%M:%S')}\t{tag}\n")
            print(f"{name}: workflow {match.group(1)}")
        if i + 1 < len(todo) and args.delay > 0:
            time.sleep(args.delay)

    if failed:
        sys.exit(f"{len(failed)} failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
