#!/usr/bin/env python3
"""Paired per-event summary of a scan: mean +- SEM of each point, and the point-minus-reference difference
(paired by event, so shared event-to-event fluctuations cancel).

Usage: scan_table.py compare.json [--ref new_default] [--reco sparse3d_reco_rescaled] [--cls all] [--tol 2]
       [--sort metric]   (metrics: n_reco eff eff_e ghost n_ghost)
Differences more than 2 SEM from zero are marked with '*'.
"""
import argparse, json
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("json")
ap.add_argument("--ref", default="new_default")
ap.add_argument("--reco", default="sparse3d_reco_rescaled")
ap.add_argument("--cls", default="all")
ap.add_argument("--tol", type=int, default=2)
a = ap.parse_args()

d = json.load(open(a.json))
M = ["n_reco", "eff", "eff_e", "ghost"]


def series(label):
    rows = [x for x in d[label] if x["reco"] == a.reco and x["cls"] == a.cls and x["tol"] == a.tol]
    rows.sort(key=lambda x: x["event"])
    return {k: np.array([x[k] for x in rows], float) for k in M}


ref = series(a.ref)
print(f"reco={a.reco} cls={a.cls} tol={a.tol} ref={a.ref} ({len(ref['eff'])} events); diff = point - ref, '*' = >2 SEM")
print(f"{'point':<18}" + "".join(f"{k:>11}{'d'+k:>16}" for k in M))
for label in d:
    s = series(label)
    line = f"{label:<18}"
    for k in M:
        diff = s[k] - ref[k]
        sem = diff.std(ddof=1) / np.sqrt(len(diff)) if len(diff) > 1 else 0
        mark = "*" if sem > 0 and abs(diff.mean()) > 2 * sem else " "
        fmt = "{:>11.0f}{:>+12.0f}±{:<3.0f}{}" if k == "n_reco" else "{:>11.3f}{:>+12.4f}±{:<3.0f}{}"
        err = sem if k == "n_reco" else sem * 1e4
        line += fmt.format(s[k].mean(), diff.mean(), err, mark) if k != "n_reco" else fmt.format(s[k].mean(), diff.mean(), err, mark)
    print(line)
print("(errors on eff/eff_e/ghost diffs are in units of 1e-4)")
