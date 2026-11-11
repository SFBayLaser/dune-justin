#!/usr/bin/env python3
"""Which per-point features separate true from false space points?  (numpy only; host python:  /usr/bin/python3 sp_features.py point_dir [--f 0.05 --delta 0.2])

Input: point_dir/points.npy + points_cols.json written by `sp_truth_dep.py --dump` (one row per point of the builder output, 8 events).
Label: TRUE = the point's hits share one deposit at (f, delta), i.e. dmin(f) <= delta (same definition as the scan tables); normal hits only (long == 0).
1. Univariate AUC of every raw and derived feature, for 3-hit and 2-hit points separately (0.5 = no information; the top 14 by |AUC-0.5| are shown with their direction).
2. Feature groups with a small histogram gradient-boosted classifier (own implementation; train on the first events, test on the others, split by event):
     today      = what the SpacePoint carries now: chi2, err1 (total charge), err3 (charge asymmetry), n
     +builder   = + features only the builder knows: hit sharing degree (all points / 3-hit points), competing points of the same hit pair
     +hits      = + per-hit quantities: charges and amplitudes per view, their log ratios/spreads, widths, peak-time spread
   Reported: AUC and the fraction of false points removed at 90/95/99% true-point efficiency (test events).
Positions are not used as features (geometry bias).  Usage: sp_features.py dir [--split 5] [--max-train 400000]"""
import argparse, json, os
import numpy as np

ap = argparse.ArgumentParser(); ap.add_argument("d"); ap.add_argument("--f", type=float, default=0.05); ap.add_argument("--delta", type=float, default=0.2)
ap.add_argument("--split", type=int, default=5, help="events < split train, others test"); ap.add_argument("--max-train", type=int, default=400000)
ap.add_argument("--ablate", action="store_true", help="instead of the three groups: feature sets matching what Supera passes on, with and without the builder features")
ap.add_argument("--rounds", type=int, default=120); ap.add_argument("--depth", type=int, default=4)
a = ap.parse_args()
A = np.load(os.path.join(a.d, "points.npy")); cols = json.load(open(os.path.join(a.d, "points_cols.json"))); C = {c: A[:, i] for i, c in enumerate(cols)}
dm = C[f"dmin_f{a.f:g}"]; y_all = (dm <= a.delta).astype(np.float32)
sel = C["long"] == 0
print(f"{a.d}: {len(A)} points, {int(sel.sum())} normal; true fraction n=3: {y_all[sel & (C['n'] == 3)].mean():.3f}, n=2: {y_all[sel & (C['n'] == 2)].mean():.4f}")

nanl = lambda v: np.log(np.maximum(v, 1.))
q = np.stack([C["qU"], C["qV"], C["qW"]], 1); am = np.stack([C["ampU"], C["ampV"], C["ampW"]], 1); rm = np.stack([C["rmsU"], C["rmsV"], C["rmsW"]], 1)
with np.errstate(all="ignore"):
    lq = nanl(q); la = nanl(am)
    F = {"chi2": C["chi2"], "err1_totq": C["err1_totq"], "err3_asym": C["err3_asym"], "n": C["n"], "viewmask": C["viewmask"],
         "deg_max": C["deg_max"], "deg_min": C["deg_min"], "deg_mean": C["deg_mean"], "deg3_max": C["deg3_max"], "pair_max": C["pair_max"],
         "dpeak": C["dpeak"], "qU": C["qU"], "qV": C["qV"], "qW": C["qW"], "ampU": C["ampU"], "ampV": C["ampV"], "ampW": C["ampW"],
         "rmsU": C["rmsU"], "rmsV": C["rmsV"], "rmsW": C["rmsW"],
         "lq_UW": lq[:, 0] - lq[:, 2], "lq_VW": lq[:, 1] - lq[:, 2], "lq_UV": lq[:, 0] - lq[:, 1],
         "lq_std": np.nanstd(lq, 1), "lq_range": np.nanmax(lq, 1) - np.nanmin(lq, 1), "la_std": np.nanstd(la, 1), "la_range": np.nanmax(la, 1) - np.nanmin(la, 1),
         "rms_std": np.nanstd(rm, 1), "rms_max": np.nanmax(rm, 1), "rms_min": np.nanmin(rm, 1)}
GROUPS = {"today": ["chi2", "err1_totq", "err3_asym", "n", "viewmask"],
          "+builder": ["deg_max", "deg_min", "deg_mean", "deg3_max", "pair_max"],
          "+hits": ["dpeak", "qU", "qV", "qW", "ampU", "ampV", "ampW", "rmsU", "rmsV", "rmsW", "lq_UW", "lq_VW", "lq_UV", "lq_std", "lq_range", "la_std",
                    "la_range", "rms_std", "rms_max", "rms_min"]}


def auc(score, y):
    """rank-based AUC (ties averaged by argsort of ranks of a stable sort; NaNs -> not used)"""
    m = ~np.isnan(score); s, yy = score[m], y[m]
    if yy.sum() == 0 or yy.sum() == len(yy): return float("nan")
    order = np.argsort(s, kind="mergesort"); r = np.empty(len(s)); r[order] = np.arange(1, len(s) + 1)
    # average ranks over ties
    ss = s[order]; i = 0; n = len(ss); rr = r[order]
    uniq, start, cnt = np.unique(ss, return_index=True, return_counts=True)
    avg = start + (cnt + 1) / 2.
    r2 = np.empty(n); r2[order] = np.repeat(avg, cnt)
    n1 = yy.sum(); n0 = len(yy) - n1
    return float((r2[yy == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


for nn in (3, 2):
    s = sel & (C["n"] == nn); y = y_all[s]
    print(f"\nunivariate AUC (sorted by |AUC-0.5|) for {nn}-hit normal points ({int(s.sum())} points, {int(y.sum())} true):")
    res = []
    for k, v in F.items():
        if k in ("n", "viewmask"): continue
        v = v[s]
        if np.isnan(v).all() or np.nanstd(v) == 0: continue
        sc = auc(v, y); res.append((abs(sc - 0.5), sc, k))
    for d_, sc, k in sorted(res, reverse=True)[:14]: print(f"  {k:<12}{sc:7.3f}  ({'higher=true' if sc > 0.5 else 'lower=true'})")


# ---- small histogram GBDT (binary logloss)
def bins_of(X, nb=48):
    edges = []
    for j in range(X.shape[1]):
        v = X[:, j]; v = v[np.isfinite(v)]
        e = np.unique(np.quantile(v, np.linspace(0, 1, nb + 1)[1:-1])) if len(v) else np.array([0.])
        edges.append(e)
    return edges


def binify(X, edges):
    B = np.zeros(X.shape, dtype=np.uint8)
    for j, e in enumerate(edges):
        v = X[:, j]; b = np.searchsorted(e, np.where(np.isfinite(v), v, -np.inf), side="right") + 1; b[~np.isfinite(v)] = 0; B[:, j] = b
    return B


def fit(B, y, rounds, depth, lr=0.15, nbin=50, lam=5.):
    n, p = B.shape; p0 = y.mean(); F0 = np.log(p0 / (1 - p0)); Fx = np.full(n, F0); trees = []
    for _ in range(rounds):
        pr = 1 / (1 + np.exp(-Fx)); g = pr - y; h = pr * (1 - pr) + 1e-6
        node = np.zeros(n, dtype=np.int32); tree = []
        for lev in range(depth):
            splits = {}
            for nd in np.unique(node):
                m = node == nd; best = (0., None)
                gn, hn = g[m], h[m]; G, H = gn.sum(), hn.sum(); base = G * G / (H + lam)
                for j in range(p):
                    bj = B[m, j]; gh = np.bincount(bj, weights=gn, minlength=nbin); hh = np.bincount(bj, weights=hn, minlength=nbin)
                    GL = np.cumsum(gh)[:-1]; HL = np.cumsum(hh)[:-1]; GR, HR = G - GL, H - HL
                    gain = GL * GL / (HL + lam) + GR * GR / (HR + lam) - base; gain[(HL < 20) | (HR < 20)] = -1
                    k = int(np.argmax(gain))
                    if gain[k] > best[0]: best = (gain[k], (j, k))
                if best[1] is not None: splits[nd] = best[1]
            tree.append(splits)
            newnode = node * 2 + 1
            for nd, (j, k) in splits.items():
                m = node == nd; newnode[m] = node[m] * 2 + 1 + (B[m, j] > k)
            node = newnode
        leaf = {}
        for nd in np.unique(node): m = node == nd; leaf[nd] = -g[m].sum() / (h[m].sum() + lam)
        Fx += lr * np.array([leaf[x] for x in node]) if False else lr * np.vectorize(leaf.get)(node)
        trees.append((tree, leaf))
    return F0, lr, trees


def predict(model, B):
    F0, lr, trees = model; Fx = np.full(len(B), F0)
    for tree, leaf in trees:
        node = np.zeros(len(B), dtype=np.int32)
        for splits in tree:
            newnode = node * 2 + 1
            for nd, (j, k) in splits.items():
                m = node == nd; newnode[m] = node[m] * 2 + 1 + (B[m, j] > k)
            node = newnode
        Fx += lr * np.vectorize(lambda x: leaf.get(x, 0.))(node)
    return Fx


def rejection(score, y, effs=(0.90, 0.95, 0.99)):
    out = []
    for e in effs:
        thr = np.quantile(score[y == 1], 1 - e); out.append(float((score[y == 0] < thr).mean()))
    return out


ev = C["ev"]; train = sel & (ev < a.split); test = sel & (ev >= a.split)
rng = np.random.default_rng(1)
ti = np.flatnonzero(train)
if len(ti) > a.max_train: ti = rng.choice(ti, a.max_train, replace=False)
xi = np.flatnonzero(test)
print(f"\nGBDT: train {len(ti)} points (events < {a.split}), test {len(xi)} points; test true fraction {y_all[xi].mean():.4f}")
print(f"{'features':<22}{'AUC':>7}   false points removed at true efficiency 90% / 95% / 99%")
SUPERA = ["chi2", "err1_totq", "n", "viewmask", "qU", "qV", "qW", "dpeak", "lq_UW", "lq_VW", "lq_UV", "lq_std", "lq_range"]   # charge, chi2, nhits, per-plane hit charge and time
SETS = [("supera-like", SUPERA), ("+ deg_mean, deg3_max, pair_max", SUPERA + ["deg_mean", "deg3_max", "pair_max"]),
        ("+ all builder features", SUPERA + GROUPS["+builder"]), ("+ all builder + amp/rms", SUPERA + GROUPS["+builder"] + ["ampU", "ampV", "ampW", "rmsU", "rmsV", "rmsW", "rms_std", "rms_max", "rms_min", "la_std", "la_range"])]
RUNS = [(n, k) for n, k in SETS] if a.ablate else None
if not a.ablate:
    names = []; RUNS = []
    for g in ("today", "+builder", "+hits"):
        names = names + GROUPS[g]; RUNS.append((g, list(names)))
for g, names in RUNS:
    X = np.stack([F[k] for k in names], 1).astype(np.float32)
    ed = bins_of(X[ti]); model = fit(binify(X[ti], ed), y_all[ti], a.rounds, a.depth)
    sc = predict(model, binify(X[xi], ed)); r = rejection(sc, y_all[xi])
    print(f"{g:<22}{auc(sc, y_all[xi]):7.3f}   " + " / ".join(f"{100 * v:5.1f}%" for v in r), flush=True)
    for nn in (3, 2):
        m = C["n"][xi] == nn
        if y_all[xi][m].sum() > 20: print(f"   {nn}-hit only:{'':<6}{auc(sc[m], y_all[xi][m]):7.3f}   " + " / ".join(f"{100 * v:5.1f}%" for v in rejection(sc[m], y_all[xi][m])))
