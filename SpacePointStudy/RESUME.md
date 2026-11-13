# Resume notes (written 2026-11-13, before a reboot)

## Where things are
- Study log with all results and corrections: `RUNS.md` (latest sections: ball label, false-point categories, top-n per hit, CORRECTION (float32 key bug), in-tool TopNPerHit, the 2-hit points, third-plane test).
- Truth/metric script: `sp_truth_dep.py` (`--dump --ball --ball-recall`), columns documented in the file; dump columns now include category (`c_*`), nearest voxel (`v_*`) and hit indices (`gi0..gi2`).
- Event displays: `sp_display.py` + `sp_display_template.html` (double-click sets the focal point, C re-centres). Pages (not committed, 4-27 MB): `display_sym_noexcl_top3.html`, `display_sym_noexcl.html`, `display_baseline.html`; regenerate with `analysis/disp_all.sh` in the container.
- Analysis helpers (copied from the scratchpad, edit the paths if needed): `analysis/` (runtop*.sh run the Fast tool for 8 events then the dump; sumv.py summary table; topn.py, two*.py, contest.py, sel.py, feat*.py, vx.py, brk*.py offline studies). Use `/usr/bin/python3` on the host (the PATH python3 is broken outside the container). Hit keys must be float64 (`ev*1e7+gi`).
- Slides: artifact https://claude.ai/artifact/JocDBDuv5cBqfh3E91MWDq (private, version 7), sources in `slides_src/`. Not yet in the deck: top-n per hit, 2-hit results, corrected numbers.
- Samples/outputs: `/run/media/usher/Drive2/DUNE/samples/FD_330003/hitscan_loose/<variant>` (points.npy, points_cols.json, ball_recall.txt, point.fcl, run.log).

## dunereco (branch feature/usher_spacepointoptimization, FD/v10_24_00d00/srcs/dunereco)
`SnippetHit3DBuilderDUNEFast_tool.cc` new fcl: `TopNPerHit` (0 off), `TopNRank` (chi2|time|score), `DropOrphansSharingTriplet`, `DropOrphansNeedBothHits`, `OrphanNeedsEmptyThirdPlane`, plus earlier `NoExclusivity`, `SymmetricThirdWire`, `MaxTripletsPerPair`, diagnostics. All default to the old behaviour. Installed build is current (`bld.sh ninja -j6 install` in the container after `mrbsetenv`).

## Recommended configuration so far (8 FD events, ball label)
`NoExclusivity: true`, `SymmetricThirdWire: true`, `TopNPerHit: 3`, `TopNRank: "chi2"`, `DropOrphansSharingTriplet: true`, `DropOrphansNeedBothHits: true`, MaxHitChiSquare 10 (chi-square cuts are not tuned).
Per event: ~8,980 3-hit points (65% precision), ~1,500 2-hit points, site coverage 88.2% (all hits) / 91.3% (normal) vs baseline 25,951 3-hit (14%), 111,000 2-hit, 97.3% / 95.6%.

## Next
1. Long-hit study: group the segments of each long hit and treat the group as one hit spanning its start-to-end; compare with the split segments for matching and volume, scored with the ball label (long hits are 30-39% of true points and the main source of lost site coverage and of same-particle ghosts).
2. Investigate the ~9 points of site coverage lost by top-3 (mostly long-hit sites).
3. Add the top-n and 2-hit results to the slides; check the double-click picking in the display; Supera/SPINE comparison with the nearest-voxel label; VD.
4. Nothing is pushed: dune-justin `develop` and dunereco `feature/usher_spacepointoptimization` have local commits only.
