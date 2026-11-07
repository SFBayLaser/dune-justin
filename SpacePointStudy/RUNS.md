# Space point builder validation and optimization: FD-HD and FD-VD

Goal: validate the new `SpacePointBuilderDUNE` module (Fast tool) against the standard Cluster3D
space point building, then optimize the parameters of the Fast tool.

Keep this file current. Every job or local run gets a row in the run log below.

## The two builders

| | Baseline ("standard") | New ("fast") |
|---|---|---|
| Module | `Cluster3DDUNE` with `MakeSpacePointsOnly: true` | `SpacePointBuilderDUNE` |
| Tool | `SnippetHit3DBuilderDUNE` | `SnippetHit3DBuilderDUNEFast` |
| Prolog | `standard_cluster3ddune` + `standard_snippethit3dbuilderDUNE` | `standard_spacepointbuilderdune` + `standard_snippethit3dbuilderDUNEFast` |
| Defined in | `dunereco/Cluster3D/cluster3Dmodule_dune.fcl`, `cluster3dalgorithms_dune.fcl` | same files, branch `feature/usher_spacepointoptimization` |
| `MaxHitChiSquare` | 10 (old production fhicl; tool default is 6) | 6 (tool default) |

**The `MaxHitChiSquare` mismatch is intentional for now** (baseline reproduces the old production
setting). Set both to the same value for a like-for-like comparison.

Code: `FD/v10_24_00d00/srcs/dunereco`, branch `feature/usher_spacepointoptimization`
(head `a31bacea`, 2026-09-14), on top of dunesw `v10_24_00d00`. The current dunesw tag is
`v10_26_00d05`; **stay on v10_24_00d00 for the comparison**, rebase and rerun a confirmation after tuning.

## Where the switch is made

Both builders live in the same build. Only fhicl differs.

| Detector | New builder | Baseline |
|---|---|---|
| FD-HD | `DUNESpineWorkshop2026/fhicl/standard_mythical_supera_dune10kt_1x2x6.fcl` | `..._1x2x6_baseline.fcl` |
| FD-VD | `DUNEVD/fhicl/standard_supera_dunevd10kt_1x8x6_3view_30deg.fcl` | `..._30deg_baseline.fcl` |

The module is chosen in `workflow_reco_dune10kt.fcl` / `workflow_reco_dunevd10kt.fcl`
(`cluster3d: @local::standard_spacepointbuilderdune`). The baseline files replace the whole
`physics.producers.cluster3d` table.

**History note (fixed 2026-11-02):** `standard_supera_dune10kt_1x2x6.fcl` and
`standard_reco1_dune10kt_1x2x6.fcl` set `cluster3d.Hit3DBuilderAlg: @local::standard_snippethit3dbuilderDUNE`,
which loaded the OLD tool inside the NEW module. VD fixed the same line on 2026-09-22. Any FD
"new builder" results produced before 2026-11-02 may not have exercised the Fast tool.

## Job configs (justIN)

| Config | Purpose | dunesw | Local-code tarball | Run base |
|---|---|---|---|---|
| `DUNESpineWorkshop2026/mvpmpr_2hitSP_baseline_config.json` | FD baseline, keeps detsim 14 d | v10_24_00d00 | `4de2fb4d...` | 320000 |
| `DUNESpineWorkshop2026/mvpmpr_2hitSP_testcode_config.json` | FD new builder | v10_24_00d00 | `4de2fb4d...` | 310000 |
| `DUNEVD/mpvmpr_2hitSP_baseline_config.json` | VD baseline, keeps detsim 14 d | v10_24_00d00 | `da6832fe...` | 020000 |
| `DUNEVD/mpvmpr_2hitSP_testcode_config.json` | VD new builder | v10_24_00d00 | `da6832fe...` | 010000 |
| `DUNEVD/rain_2hitSP_testcode_config.json` | VD "rain" only | v10_24_00d00 | `da6832fe...` | 010000 |

Tarball paths: `/cvmfs/fifeuser1.opensciencegrid.org/sw/dune/4de2fb4d19f920807e0a8e8b5b93dbea2c08229c` (FD)
and `/cvmfs/fifeuser2.opensciencegrid.org/sw/dune/da6832fea0b50d4148ee8495f61d87e9aa1acddd` (VD).
These are not mounted on the laptop. **The dunereco commit inside each tarball was not recorded.**
Record it (and the build date) next time a tarball is made.

Older configs (`mvpmpr_2hitSP_config.json`, `mpvmpr_2hitSP_config.json`, `*_wlocalcode_config.json`,
`atmospheric/prodgenie`) predate the new builder. The FD and VD `*_2hitSP_config.json` use releases
(v10_20_08d00, v10_21_00d00) that do not contain `standard_spacepointbuilderdune`, so they do not
work with the current fhicl bundles.

### Fhicl bundles

Jobs fetch `https://raw.githubusercontent.com/SFBayLaser/dune-justin/main/bundles/fhicl_bundle.tgz`
(FD) and `fhicl_vd_bundle.tgz` (VD) from the `main` branch. **Rebuild and push after any fhicl change:**

```
tar czf bundles/fhicl_bundle.tgz    -C DUNESpineWorkshop2026 fhicl
tar czf bundles/fhicl_vd_bundle.tgz -C DUNEVD fhicl
```

### Matched samples

The baseline workflows keep the stage-3 detsim files (14 days) so the new builder can be run
reco-only on the identical input (a `mql` workflow on the baseline detsim files). Whether justIN
accepts `output_patterns` together with `output_pattern_next_stage` on stage 3 is **untested**.
Fallback: same `RUN_BASE`, check that gen output is reproducible.

## Working locally (laptop, SL7 container)

```
apptainer shell --shell=/bin/bash -B /cvmfs,/run/media/usher/Drive2,/run/media/usher/Drive2:/media/usher/Drive2 \
    --pwd /run/media/usher/Drive2 --ipc --pid ~/test/fnal-dev-sl7.sif
source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh
cd FD/v10_24_00d00 && source ./localProducts_larsoft_v10_24_00_e26_prof/setup
setup dunesw v10_24_00d00 -q e26:prof
```

* The extra `-B ...:/media/usher/Drive2` bind is required: the localProducts `setup` script
  hard-codes `/media/usher/Drive2`, and without it the build is silently skipped and cvmfs dunereco is
  used (`ups active | grep dunereco` must show `-z .../localProducts_...`).
* Check a fhicl: `FHICL_FILE_PATH=<fhicl dir>:$FHICL_FILE_PATH lar -c X.fcl --debug-config out.txt`.
* justIN/rucio: `setup justin; justin get-token; setup rucio`. Submission only from a DUNE gpvm.

### Truth comparison

`SpacePointStudy/compare_truth.py` compares `sparse3d_reco` and `sparse3d_reco_rescaled` against the
truth deposits `sparse3d_sed` in the Supera `larcv.root`, using voxel neighbourhoods of radius r:
efficiency (plain and energy-weighted) and ghost fraction. Needs the cvmfs larcv2 v2_3_2 through
PyROOT (`SpacePointStudy/larcv_env.sh`; there is no python larcv module). Voxels are ~0.48 cm, so
r = 2 is ~1 cm. `SpacePointStudy/run_fd_local.sh [N]` runs both builders on the 27 Aug FD detsim file
and compares them.

### Fast scans (second pass)

`DUNESpineWorkshop2026/fhicl/supera_sponly_dune10kt_1x2x6[_baseline].fcl` rerun only the builder + Supera on an
existing `*_supera.root` (it already holds `gaushit`, `mcreco`, sed, simchannels). Verified 2026-11-02: voxel-for-voxel
identical to the full chain on 3 events. Cost is dominated by the Supera driver (about 37 s/event versus 1.6 s for
the builder), so the saving is only the upstream reconstruction; run points **in parallel**
(each ~1.3 GB, 1 core): `SpacePointStudy/run_scan.py <spec.json> --jobs 7`. A spec lists points as
`{builder, params}` on top of `common` params. First spec: `scan_points_fd_first.json`.
A point counts as finished only if `time.log` has `Exit status: 0`.

### What the truth tool reports

`compare_truth.py` splits reco points by hit multiplicity (`sparse3d_reco_nhits`): `3hit` = triplets,
`2hit` = "mythical" two-plane points. It also reports `n_ghost` and can emulate chi-square cuts offline
(`--max-chi2-3hit`, `--max-chi2-2hit`), because each point's chi2 is stored (`sparse3d_reco_chi2`).
Facts established from the stored values: 2-hit chi2 is capped exactly at `DeltaPeakTimeSig`^2 (3.06 baseline,
4.0 new), so `MaxMythicalChiSquare = 25` never acts; 3-hit chi2 tops out at `MaxHitChiSquare`.

## Run log

| Date | Where | What | Events | Result / location |
|---|---|---|---|---|
| 2026-08-27 | laptop, `FD/workarea` | FD supera slow vs fast (before the FD override fix) | 100 | `*_supera.root`, `*_supera_fast.root`, `slow.log`, `fast.log`. Old builder 3.1 s/event mean. Fast tool may not have been exercised (see above). |
| 2026-09 | justIN | FD and VD testcode workflows | ? | **Not recorded.** Workflow IDs and outcomes unknown. |
| 2026-11-02 | laptop, `FD/localtest` | FD supera, baseline vs new, same detsim input | 5 | Builder 1.71 s vs 1.97 s per event; 21-38% more raw space points in the new builder; efficiency and ghost fraction equal within noise at r = 2 (eff 0.685 vs 0.689, ghost 0.654 vs 0.636 raw). `FD/localtest/truth_compare.json` |
| 2026-11-02 | laptop, `FD/localtest40` | same, 40 events (`run_fd_local.sh 40`; `MaxHitChiSquare` 10 baseline / 6 new) | 40 | Builder time/event mean 2.27 s (baseline) vs 2.47 s (new); wall 39:04 vs 45:56; peak RSS 3.49 vs 3.81 GB. Raw points/event 181k vs 207k (+14%); after Supera cuts 16.8k vs 21.0k (+25%). At r = 2: raw eff 0.705 vs 0.709, ghost 0.692 vs 0.679; after cuts eff 0.624 vs 0.628, ghost 0.049 vs 0.047 (energy-weighted eff 0.882 vs 0.885). `FD/localtest40/truth_compare.json` |
| 2026-11-02 | laptop, `FD/localtest40` | class split of the above (r = 2, raw points) | 40 | 3-hit: 34.1k (baseline) vs 47.1k (new), ghost fraction 0.279 vs 0.281, eff 0.632 vs 0.638. 2-hit: 147k vs 160k, ghost 0.787 vs 0.799, eff 0.669 vs 0.670. After Supera cuts 3-hit survivors +39% at equal ghost fraction (0.044 vs 0.043); 2-hit survivors -10% with lower efficiency (0.525 vs 0.503). Excess is in 3-hit points and looks real (not ghosts); 2-hit points are ~85% of raw points but ~25% of survivors. `FD/localtest40/truth_compare_cls.json` |
| 2026-11-02 | laptop, `FD/scan_first` | first FD scan, 7 points, `MaxHitChiSquare` 10 for all (see `scan_points_fd_first.json`) | 40 | Done, `FD/scan_first/compare.txt`. Raw 3hit/2hit pts per event (ghost frac), r = 2: baseline 34.1k/147k (0.279/0.787); new_default 49.4k/157k (0.286/0.805); dts175 45.0k/147k (0.272/0.792); dts150 38.8k/134k (0.258/0.776); no2hit 49.4k/0. After Supera cuts (all classes, eff / eff(E) / ghost): baseline 0.624/0.882/0.049; default 0.628/0.885/0.047; dts175 0.627/0.885/0.047; dts150 0.625/0.882/0.047; no2hit 0.600/0.862/0.044. WirePitchScaleFactor 1.5 and PulseHeightFraction 0.6 changed nothing (within 1%). Timing from this scan is not usable (7 jobs in parallel contend). |
| 2026-11-03 | laptop, `FD/scan_second` | second FD scan, 27 points (`scan_points_fd_second.json`), tool rebuilt with new `MaxTripletsPerPair` (dunereco `8a986278`), `MaxHitChiSquare` 10 for all. Summarized with `scan_table.py` (paired per-event, ref `new_default`, after Supera cuts, r = 2) via `compare_parallel.sh` | 40 | `FD/scan_second/compare.json`. **No parameter gives a large gain.** Inert (<0.1% change in points and efficiency): `HitWidthScaleFactor` (1.5, 4.0), `RangeNumSigma` (2, 4), `MaxMythicalPointsPerWire` 64, `MaxTripletsPerPair` 4 and 64 (cap of 2 only -1% points), `PulseHeightFraction` (0.2, 0.8), `PHLowSelection` (4, 16; <=0.2% points). `DeltaPeakTimeSig` is a smooth trade of points vs efficiency (both short/long = 1.0: -24% points, eff -0.010; 1.25: -15%, -0.006; 1.5: -9%, -0.0035; 1.75: -3%, -0.001) with ghost fraction unchanged; long-hit cut alone is weak (1.5: -3%, -0.0006). `MinPHFor2HitPoints` 12 is bad (2-hit eff -0.052, total -0.009). `WirePitchScaleFactor` is the second real knob: 1.0 gives -14% points at eff -0.0013 but ghost +0.0017; 3.0 gives +7% points at eff +0.0005, ghost -0.0014 (3-hit class +7%). no2hit: eff -0.029 (energy-weighted -0.023). baseline vs new_default (paired): eff -0.0036, ghost +0.0020, points -20%; all >6 SEM, but small. |
| 2026-11-03 | laptop, `samples/FD_330001`, `samples/VD_20001` | new local samples via `make_sample_local.sh` (gen run 330001 FD 40 ev; 20001 VD 20 ev; wall FD gen 1 / g4 9 / detsim 45 / supera 32 min, VD 1 / 5 / 33 / 15 min), then 15-point scans (`scan_points_fd_sample2.json`, `scan_points_vd_first.json`), paired vs `new_default`, after Supera cuts, r = 2 | 40 / 20 | **FD sample 2 confirms FD sample 1**: baseline eff -0.0027 / ghost +0.0015, points -20%; dts 1.75/1.5/1.25/1.0 (both): points -3/-9/-15/-23%, eff -0.0006/-0.002/-0.0036/-0.0056; pwr 1.0/2.5/3.0: points -13/+3/+8%, eff -0.0007/+0.0004/+0.0007; no2hit eff -0.026 (E-weighted -0.022); minph2_8 eff -0.0033; phlow4, tpp2, mpw4 ~0. **VD behaves the same way but with much smaller effects**: ghost fraction 0.001 everywhere (no sensitivity), eff 0.592, E-weighted 0.939; baseline eff -0.0018, points -11%; dts 1.75/1.5/1.25/1.0: points -3/-7/-13/-19%, eff -0.0009/-0.0023/-0.0036/-0.0057; no2hit points -21%, eff -0.0097 (E-weighted -0.003); pwr30 +4% points eff +0.0011; minph2_8 -0.0022. Efficiency vs truth-voxel energy (FD sample 1, 10 ev, `eff_vs_energy.py`): voxels <0.2 MeV (49% of voxels, 6% of energy) have raw eff 0.39-0.59, voxels >0.5 MeV 0.93-0.95 (after Supera cuts 0.76 at 0.2-0.5, 0.90-0.93 above 0.5). Compare tables: `samples/*/scan/compare.json`. |
| 2026-11-06 | laptop, `samples/FD_330001`, `samples/VD_20001` | time-offset question from the meeting. Generator fhicl: `G4Time` 5000 ns, `G4TimeJitter` 10000 ns for both vertex and rain generators, FD and VD. At ~1.6 mm/us that is up to ~1.6 cm (~3 voxels) along the drift (x) axis. `drift_shift.py` (fraction of truth voxels >0.5 MeV with a reco voxel at truth + s along an axis, others within +-1) and `drift_tolerance.py` (rx along x, ry = rz = 2), new_default, first 8 events | 8 | x is broader than y and z and peaks at s = -1 voxel (FD 0.654 vs 0.595 at 0; VD 0.762 at -1, 0.720 at -2, 0.619 at 0), while y and z peak at 0 (0.74-0.78). Widening only x from 2 to 4: FD eff 0.660 -> 0.684, E-weighted 0.914 -> 0.932, truth voxels >0.5 MeV 0.951 -> 0.965, ghost fraction 0.013 -> 0.001; VD eff 0.614 -> 0.643, E-weighted 0.945 -> 0.952. Baseline builder is the same within 0.002, so the builder comparison is not affected. Not shown: whether the shift comes from the per-particle time or from hit-time/peak-time effects (field response, diffusion); needs truth time per particle, or a sample with `G4TimeJitter` 0. |
| | justIN | FD baseline (`mvpmpr_2hitSP_baseline_config.json`) | 10 x 20 | not yet submitted |
| | justIN | VD baseline (`mpvmpr_2hitSP_baseline_config.json`) | 10 x 20 | not yet submitted |

## Plan

1. Local FD (2 files) and VD (1 file) done; more files / seeds still useful.
2. Submit FD and VD baselines from a gpvm (needs the push to `main`). Record workflow IDs above.
3. Run the new builder reco-only on the baseline detsim files; compare with `compare_truth.py`.
4. Parameter scan of `SnippetHit3DBuilderDUNEFast`: `DeltaPeakTimeSig`, `DeltaPeakTimeSigLongHit`,
   `HitWidthScaleFactor`, `MaxHitChiSquare`, `MaxMythicalChiSquare`, `MaxMythicalPointsPerWire`,
   `WirePitchScaleFactor`. Run the reco stage only, on a fixed detsim sample.
5. Confirm the best settings with SPINE-level metrics and on dunesw v10_26_00d05.

## No-jitter check of the drift-axis (x) offset (2026-11-06)

Samples regenerated with `G4TimeJitter: 0` (`mpvmpr_gen_1x2x6_nojitter.fcl`, `mpvmpr_gen_vd_1x8x6_nojitter.fcl`):
`samples/FD_330002` (40 ev), `samples/VD_20002` (20 ev). Compared with the jittered `FD_330001`, `VD_20001`
using `drift_shift.py` and `drift_tolerance.py` (first 8 events, new builder, ry = rz = 2).

| sample | x peak shift (voxels) | frac at peak | y max frac | eff rx=2 / 4 | ghost rx=2 / 4 |
|---|---|---|---|---|---|
| FD jitter | -1 | 0.654 | 0.746 | 0.661 / 0.684 | 0.013 / 0.001 |
| FD no jitter | +2 | 0.614 | 0.624 | 0.638 / 0.661 | 0.014 / 0.001 |
| VD jitter | -1 | 0.764 | 0.785 | 0.614 / 0.643 | 0.001 / 0.000 |
| VD no jitter | -1 | 0.886 | 0.870 | 0.612 / 0.637 | 0.000 / 0.000 |

Without jitter the x distribution is as sharp as y and z (jitter broadened it), but a constant offset remains
(FD +2, VD -1 voxels), so the x-tolerance sensitivity persists. The remaining offset is a systematic between truth
and reco x (t0 convention, e.g. G4Time 5000 ns is ~0.8 cm at 1.6 mm/us), not a per-particle effect.

## Hit-level truth matching (gallery) (2026-11-07)

`sp_truth_purity.py`: reads the art file with gallery from PyROOT (setup dunesw, then `setup gallery v1_22_06 -q e26:prof`;
no galleryUtils needed). Each cluster3d hit -> dominant particle via `SimChannel::TrackIDEs(start, end)` (abs(trackID));
each space point is pure / partial / mixed / untruthed. SimChannel IDEs carry x, y, z, so a positional check is possible too.
First look, FD_330002 events 7 and 11, new builder, raw (before Supera cuts):

| hits | points | pure | partial | mixed | untruthed |
|---|---|---|---|---|---|
| 3 | 8664 | 95.3% | 2.9% | 0.8% | 1.1% |
| 2 | 25149 | 63.6% | n/a | 35.6% | 0.9% |

## G4Time = 0 check (2026-11-07)

Samples with `G4Time: 0` and `G4TimeJitter: 0` (`mpvmpr_gen_1x2x6_notime.fcl`, `mpvmpr_gen_vd_1x8x6_notime.fcl`): `samples/FD_330003` (20 ev), `samples/VD_20003` (10 ev).
Voxel sizes from the Supera metadata: FD 0.479 cm (x range +-552 cm, 2304 voxels), VD 0.766 cm (+-325 cm, 849 voxels).
`drift_shift_side.py` (x shift per x bin, first 8 events): peak shift is 0 in all four bins in both FD and VD, fraction at peak 0.74 to 0.91.
So the earlier offset (FD -2/+2 by drift volume, VD -1) is the 5 us generation time against a clock that starts at 0 (`detectorclocks_dune.fcl`: G4RefTime 0, TriggerOffsetTPC 0).
`drift_tolerance.py`, 20 events, new builder, ry = rz = 2, rx = 2 / 4:

| sample | eff | eff(E) | eff > 0.5 MeV | ghost |
|---|---|---|---|---|
| FD_330003 (t0 = 0) | 0.643 / 0.656 | 0.904 / 0.907 | 0.951 / 0.953 | 0.003 / 0.001 |
| FD_330002 (t0 = 5 us, no jitter) | 0.650 / 0.672 | 0.922 / 0.933 | 0.956 / 0.966 | 0.011 / 0.001 |
| FD_330001 (t0 = 5 us + jitter) | 0.633 / 0.666 | 0.896 / 0.926 | 0.934 / 0.962 | 0.024 / 0.002 |

Removing the offset cuts the r = 2 ghost fraction from 0.011 to 0.003 and shrinks the gain from a wider x tolerance (+0.013 against +0.022),
but the efficiency itself does not rise (different events, 20 each). A small x sensitivity remains.

## Baseline vs new builder with art output, hit-level purity (2026-11-07)

Sample `samples/FD_330003` (t0 = 0, no jitter). `scan_points_fd_art_notime.json` reruns cluster3d + Supera for `baseline` and `new_default`
(MaxHitChiSquare 10, 20 events) with `supera_sponly_dune10kt_1x2x6[_baseline]_art.fcl`, which also write `sp_art.root`
(cluster3d products, SimChannels, MCParticles, gaushit; ~0.5 GB per point) into `samples/FD_330003/artcmp/<point>/`.
`sp_truth_purity.py` on events 0 to 7, raw space points (before Supera cuts):

| builder | hits | points | pure | partial | mixed | untruthed |
|---|---|---|---|---|---|---|
| baseline | 3 | 207,607 | 84.6% | 9.1% | 6.2% | 0.2% |
| new | 3 | 439,165 | 85.3% | 8.7% | 5.9% | 0.1% |
| baseline | 2 | 890,868 | 64.5% | n/a | 35.3% | 0.2% |
| new | 2 | 943,885 | 63.2% | n/a | 36.6% | 0.2% |

`theta_inefficiency.py` (truth voxels of `cluster3d_sed` per particle, direction from `particle_pcluster`, theta_x folded to 0-90 deg,
r = 2, particles with >= 20 voxels, 20 events; 1 - efficiency, baseline / new):

| theta_x | 0-10 | 10-20 | 20-30 | 30-40 | 40-50 | 50-60 | 60-70 | 70-80 | 80-90 |
|---|---|---|---|---|---|---|---|---|---|
| voxels (baseline) | 279 | 6270 | 17103 | 13833 | 24497 | 56512 | 27348 | 98123 | 46046 |
| 1 - eff baseline | 0.032 | 0.290 | 0.345 | 0.235 | 0.266 | 0.299 | 0.215 | 0.339 | 0.333 |
| 1 - eff new | 0.032 | 0.286 | 0.344 | 0.235 | 0.265 | 0.297 | 0.214 | 0.338 | 0.332 |
| 1 - eff(E) baseline | 0.005 | 0.073 | 0.055 | 0.034 | 0.046 | 0.049 | 0.039 | 0.055 | 0.053 |

Json in `samples/FD_330003/artcmp/theta.json`.
