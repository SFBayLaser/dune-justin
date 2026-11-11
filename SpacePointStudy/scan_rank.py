#!/usr/bin/env python3
"""Rank the points of a hit-level scan for the 'as loose as the volume allows' goal (precision is left to the SPINE deghosting).
Usage: scan_rank.py scan_dir [--ref new_default] [--pf 0.05 --pd 0.2] [--budget 1.5]
Columns (normal hits = no long-hit segment; long hits only as cost): points/event (all, 3-hit normal, 3-hit long), true 3-hit points/event,
recall (fraction of the builder-independent truth triples built as 3-hit points), recall "any" (also as 2-hit pair), and relative to --ref:
volume (all points / ref) and the true 3-hit points gained per additional point. 'ok' = total points/event <= budget x ref.
Run with /usr/bin/python3."""
import argparse, json, os
ap = argparse.ArgumentParser(); ap.add_argument("d"); ap.add_argument("--ref", default="new_default"); ap.add_argument("--pf", type=float, default=0.05)
ap.add_argument("--pd", type=float, default=0.2); ap.add_argument("--budget", type=float, default=1.5); a = ap.parse_args()
rows = {}
for n in sorted(os.listdir(a.d)):
    f = os.path.join(a.d, n, "dep_eval.json")
    if os.path.exists(f): rows[n] = json.load(open(f))
k = f"{a.pf:g}|{a.pd:g}"
def stats(r):
    ne = r["events"]; x = r["res"][k]; N, L = x["normal"], x["long"]
    return dict(allp=(N["n3"] + N["n2"] + L["n3"] + L["n2"]) / ne, n3=N["n3"] / ne, l3=L["n3"] / ne, t3=N["true3"] / ne,
                rec=100 * N["rec"] / max(1, N["T"]), any=100 * N["recany"] / max(1, N["T"]), recE=100 * N["recw"] / max(1e-30, N["Tw"]), frac=100 * N["true3"] / max(1, N["n3"]))
S = {n: stats(r) for n, r in rows.items()}
ref = S.get(a.ref)
print(f"normal-hit truth at f>={a.pf:g}, delta<={a.pd:g} cm; reference {a.ref}; budget = {a.budget:g} x reference points/event")
print(f"{'point':<14}{'pts/ev':>9}{'3h norm':>9}{'3h long':>9}{'true3/ev':>9}{'frac':>6}{'recall':>8}{'E-w':>6}{'any':>6}{'vol/ref':>8}{'d true3':>9}{'per 1k pts':>11}  ok")
for n, s in sorted(S.items(), key=lambda kv: -kv[1]["rec"]):
    vol = s["allp"] / ref["allp"] if ref else float("nan")
    dt = s["t3"] - ref["t3"] if ref else float("nan"); dp = s["allp"] - ref["allp"] if ref else float("nan")
    gain = f"{1000 * dt / dp:11.1f}" if ref and abs(dp) > 1 else f"{'-':>11}"
    print(f"{n:<14}{s['allp']:9.0f}{s['n3']:9.0f}{s['l3']:9.0f}{s['t3']:9.0f}{s['frac']:5.1f}%{s['rec']:7.1f}%{s['recE']:5.1f}%{s['any']:5.1f}%{vol:8.2f}{dt:9.0f}{gain}  {'yes' if vol <= a.budget else 'no'}")
