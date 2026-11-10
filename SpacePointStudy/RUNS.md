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

## Positional truth check of pure points (2026-11-08)

`sp_truth_pos.py` (wrapper `run_sp_truth_pos.sh art_file.root [args]`) extends `sp_truth_purity.py`: the dominant particle per hit is now
summed over abs(trackID) from `SimChannel::TDCIDEMap()` (equivalent to the old result: event 0 gives the same purity in both scripts), and each
hit keeps the x, y, z of that particle's IDEs in the hit's tick range. d_hit = 3D distance from the space point to the nearest such IDE; d_point = max over hits.
"ok < tol" = pure and d_point < tol. Needs `sim::IDE` dictionary: `gInterpreter.Declare('#include "lardataobj/Simulation/SimChannel.h"')` after
loading `liblardataobj_Simulation` (not the `_dict` lib), and a C++ helper for `SpacePoint::XYZ()` (PyROOT misreads the pointer).
`samples/FD_330003/artcmp`, events 0 to 7, raw points before Supera cuts (`pos_baseline.txt`, `pos_new_default.txt`, `.json`):

| builder | hits | points | pure | ok<0.5 cm | ok<1 | ok<2 | ok<5 | pure but d>=5 cm | mixed |
|---|---|---|---|---|---|---|---|---|---|
| baseline | 3 | 207,607 | 84.5% | 14.1% | 24.3% | 33.0% | 45.0% | 39.5% | 6.2% |
| new | 3 | 439,165 | 85.3% | 12.4% | 22.1% | 30.7% | 43.2% | 42.1% | 5.9% |
| baseline | 2 | 890,868 | 64.5% | 1.2% | 3.4% | 6.6% | 12.9% | 51.6% | 35.3% |
| new | 2 | 943,885 | 63.2% | 1.0% | 2.7% | 5.5% | 11.7% | 51.6% | 36.6% |

Median d_point of pure points: 3-hit 4.1 (baseline) / 4.3 cm (new), 2-hit 22 cm for both.
The particle-only purity overstates correct points a lot: about half of the pure 3-hit points are 5 cm or more from any deposit of that particle
that the hits could come from. The offsets are in y and z, not x (events 1 and 2, new builder: median |dx| 0.1 to 0.2 cm for all d bins; |dy|, |dz| of
9 and 6 cm in the 5 to 30 cm bin), so these are same-particle wrong crossings (ghosts along a long track or shower), not a t0 or drift offset.
The two builders are again close; the new one has slightly lower correct fractions at fixed tolerance but makes 2.1x more 3-hit points.
Caveats: d_hit is per hit (nearest IDE), so it is looser than requiring one common truth position; the first 8 events have a lot of shower activity (event 0:
pure 26% for 2-hit). Completeness (fraction of true cross-plane combinations that become a point) is not computed yet.

## Hit-level scan driver (2026-11-08)

`run_hit_scan.py spec.json` (run with `/usr/bin/python3`; the duneEnv python3 first in PATH lacks libpython) runs, per point, only the builder
(`DUNESpineWorkshop2026/fhicl/sp_hit_dune10kt_1x2x6[_baseline].fcl`: no Supera, writes a small `sp_art.root` with cluster3d + gaushit, SimChannels are read
from the input file), then `sp_truth_scan.py` (container, `gallery_env.sh`) writes `hit_eval.json/txt` per point and `hit_table.txt`; truth cache `truth_cache.pkl`.
Test spec `scan_hit_fd_test.json` (FD_330003, 8 events, 3 points, 4.5 min total, 6 in parallel; reco ~45 s per point). Table (ok = pure and within 2 cm of a deposit of that particle):

| point | pts/ev 3-hit | pts/ev 2-hit | pure 3h | ok 3h | ok 2h | mixed 3h | mixed 2h | hits in >= 1 point | hits in >= 1 ok point | same, E-weighted |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 25951 | 111358 | 84.5% | 33.0% | 6.6% | 6.2% | 35.3% | 96.9% | 93.2% | 96.8% |
| new_default | 54896 | 117986 | 85.3% | 30.7% | 5.5% | 5.9% | 36.6% | 97.1% | 93.8% | 97.1% |
| new_chi5 (MaxHitChiSquare 5) | 47582 | 124747 | 86.1% | 32.3% | 6.3% | 5.5% | 35.6% | 97.1% | 93.9% | 97.3% |

The first two rows reproduce the `sp_truth_pos.py` numbers. Completeness here is hit recovery: the fraction of truthed gaushit hits in at least one correct point (per view 92.7 to 94.4%).
It is weak as a discriminator (93 to 94% for all three, since one correct point out of many per hit is enough); a stricter version (per truth deposit or per
particle-plane-crossing) would be needed if hit recovery is to constrain the scan. Correct-point fraction and points per event move more.

## What are the extra points of the new builder? (2026-11-08)

`sp_compare_sets.py A_dir B_dir --cache truth_cache.pkl` matches points of two builders by hit set (hit key = event, channel, start, end, peak). `hitscan_test`, baseline vs new_default,
events 0 to 7, ok = pure and within 2 cm (`hitscan_test/compare_sets_baseline_new.txt`). Hit sets are never duplicated inside one builder and the position of a shared hit set is identical
in both (0 of 992,395 differ by more than 0.01 cm), so the builders differ only in which hit combinations they accept.
New 3-hit points (439,165): 176,919 shared with baseline (31.1% ok), 86,292 "superset" (contain a pair that baseline has only as a 2-hit point; 27.2% ok), 175,851 "recombined" (all three hits
used by baseline but never together; 32.1% ok), 103 with a hit baseline never uses. Baseline 3-hit points missing in the new builder: 30,687 (16,787 recombined, 46.1% ok; 13,900 superset, 41.1% ok).
New 2-hit extras: 114,161 recombined (8.9% ok), 14,141 subset; baseline has 74,745 2-hit points that the new builder promoted to 3-hit (31.3% ok).
Hits in 3-hit points: 47,328 (baseline) vs 47,606 (new), so the same hits are used; 3-hit points per hit 13.2 vs 27.7. The extras are as good as the shared ones (ok 27 to 32% vs 31%), not better.

## Feasibility of deposit-level truth matching (2026-11-09)

`sp_ide_check.py` and `sp_ide_nn.py` (container, `gallery_env.sh`; FD_330003 supera file, events 3 and 0). IDEs on channels that carry hits.
* Exact (abs(trackID), x, y, z) keys are not shared across planes: 92 to 94% of the energy has a key seen in one plane only (3 planes: 4 to 5%). IDE positions are per channel/TDC averages, not per G4 step. Rounding to 0.1 cm gives 70 to 77% of the energy in 3 planes, but that is a grid artefact.
* Nearest same-particle IDE on the other plane (energy-weighted, for each W-plane IDE): within 0.05 cm for 85 to 96%, within 0.1 cm for 94 to 99%, within 0.2 cm for 98 to 99%, none within 0.5 cm for 0.2 to 0.9%. So proximity (0.1 to 0.2 cm) works, identity does not. This cannot tell the same deposit from a neighbouring step of the same particle, but that is far below the wire pitch (0.48 cm).
* Hit windows vs IDE TDC: the energy-weighted IDE TDC lies about 1.1 ticks before the hit PeakTime (same in U, V, W); for 99.6 to 100% of hits there is IDE energy inside [StartTick, EndTick], and the median fraction of the energy within +-30 ticks that is inside [start, end] is 1.00. No window shift is needed.

## Deposit-level truth metric (2026-11-09)

SimChannels are from the WireCell drift simulation, not G4, so IDE positions are per channel/TDC (weighted) values and differ between planes; exact (trackID,x,y,z) keys are shared across planes for only 4 to 5% of the energy,
and the single-plane keys are spread evenly over U, V, W (about 31% each; `sp_ide_planes.py`). Matching is by proximity instead.
`sp_truth_dep.py` (also run by `run_hit_scan.py --dep`, tables in `dep_table.txt`, per point `dep_eval.json/txt`; cache `truth_ide_cache.pkl`): per hit the IDEs in [StartTick, EndTick] are summed per particle and per 0.2 cm voxel;
a point is TRUE when one voxel per hit, same abs(trackID), each with at least a fraction f of its hit's energy, lie pairwise within delta of each other (smallest max pairwise distance searched below 0.5 cm).
Truth triples = all (U,V,W) hit sets with a common deposit (builder independent); recall = fraction built as 3-hit points (E-w: weighted by the smallest voxel energy; any: also a 2-hit point of one of its pairs).
`hitscan_test`, FD_330003, events 0 to 7, raw points, delta 0.2 cm:

| f | point | 3-hit pts/ev | true 3h | true 3h /ev | true 2h /ev | truth triples/ev | recall | E-w | any |
|---|---|---|---|---|---|---|---|---|---|
| 0.01 | baseline | 25951 | 12.7% | 3295 | 2625 | 58913 | 5.6% | 4.7% | 17.2% |
| 0.01 | new_default | 54896 | 10.6% | 5815 | 2252 | 58913 | 9.9% | 8.9% | 19.7% |
| 0.01 | new_chi5 | 47582 | 11.5% | 5451 | 2737 | 58913 | 9.3% | 8.4% | 21.5% |
| 0.05 | baseline | 25951 | 5.9% | 1543 | 1150 | 11160 | 13.8% | 7.9% | 29.9% |
| 0.05 | new_default | 54896 | 4.1% | 2236 | 1039 | 11160 | 20.0% | 12.5% | 35.5% |
| 0.05 | new_chi5 | 47582 | 4.5% | 2145 | 1208 | 11160 | 19.2% | 12.0% | 37.5% |
| 0.2 | baseline | 25951 | 1.7% | 436 | 343 | 1749 | 24.9% | 9.2% | 42.0% |
| 0.2 | new_default | 54896 | 1.0% | 549 | 304 | 1749 | 31.4% | 13.1% | 51.0% |
| 0.2 | new_chi5 | 47582 | 1.1% | 544 | 325 | 1749 | 31.1% | 13.0% | 51.7% |

Median distance point to matched deposit centroid for true 3-hit points: 0.3 to 0.4 cm (f 0.01, delta 0.2). Widening delta to 0.4 changes the true 3-hit fraction only from 12.7% to 15.2% (baseline, f 0.01).
Only a few % of the 3-hit points share a deposit across their three hits (5 to 13%, against 85% "pure" and 31 to 33% "ok" in the per-hit metrics). The new builder makes 1.3 to 1.8 times as many true 3-hit points per event as the baseline but a lower fraction.
Not yet validated against an oracle or the Supera-level efficiency; the absolute scale depends on f and on the hit [start, end] windows.

## Oracle check of the deposit metric and long hits (2026-11-09)

**Long hits** (`sp_longhits.py`): pulses too long for one Gaussian are cut into evenly spaced segments: `DegreesOfFreedom == 1` (not < 1), RMS 3.3, peaks about 10 ticks apart (gap CV 0.07 to 0.09), up to 20 segments,
all segments sharing the pulse's [StartTick, EndTick]. They are 3.3 to 21.6% of the gaushit hits (events 3, 0, 2) but 20 to 78% of the 3-hit points and 14 to 61% of the 2-hit points contain at least one.
In `sp_truth_dep.py` each segment now gets its own tick window (split at the midpoints between neighbouring peaks), and points / truth triples are classed `normal` (no long hit) or `long`; tables use `--cls` (default normal).

**Oracle** (`sp_truth_dep.py point_dir --oracle`, FD_330003 events 0 to 7, up to 4000 normal truth triples per event; % judged TRUE by the metric):

| f | delta | truth triples as points | W hit shifted by 1 channel | 2 | 3 | 5 | 10 | random W hit | recall with a random 30% as points |
|---|---|---|---|---|---|---|---|---|---|
| 0.01 | 0.2 | 100% | 53.3% | 13.0% | 1.1% | 0.0% | 0.0% | 0.3% | 30.0% |
| 0.01 | 0.4 | 100% | 58.6% | 20.3% | 2.6% | 0.0% | 0.0% | 0.4% | 30.0% |
| 0.05 | 0.2 | 100% | 42.5% | 3.9% | 0.0% | 0.0% | 0.0% | 0.2% | 30.0% |
| 0.05 | 0.4 | 100% | 51.6% | 9.1% | 0.3% | 0.0% | 0.0% | 0.2% | 29.9% |
| 0.2 | 0.2 | 100% | 35.3% | 0.3% | 0.0% | 0.0% | 0.0% | 0.1% | 30.3% |
| 0.2 | 0.4 | 100% | 49.4% | 1.6% | 0.0% | 0.0% | 0.0% | 0.1% | 30.1% |

Shifted hit = nearest-peak normal W hit (within 15 ticks) on channel +-k of the original. The metric reproduces the truth set, rejects random hits (0.1 to 0.4%) and wrong hits 3 or more channels away (<= 2.6%),
and accepts a hit on the adjacent wire for 35 to 59% (charge sharing: a deposit is seen on neighbouring wires, so the resolution is about one wire; channel +-1 is assumed to be spatial neighbours, not checked at plane wraps).

**Baseline vs new, normal and long separately** (`hitscan_test`, events 0 to 7, delta 0.2 cm, `sp_truth_dep.py --table ... --cls`):

| f | hits | point | 3h pts/ev | true 3h | true 3h /ev | truth triples/ev | recall | E-w | any |
|---|---|---|---|---|---|---|---|---|---|
| 0.01 | normal | baseline | 11767 | 21.3% | 2505 | 25839 | 9.7% | 12.9% | 27.0% |
| 0.01 | normal | new_default | 21431 | 18.3% | 3924 | 25839 | 15.2% | 19.9% | 31.6% |
| 0.01 | normal | new_chi5 | 17958 | 20.5% | 3676 | 25839 | 14.2% | 18.7% | 34.7% |
| 0.01 | long | baseline | 14184 | 5.3% | 748 | 6222 | 12.0% | 15.2% | 34.1% |
| 0.01 | long | new_default | 33465 | 5.2% | 1734 | 6222 | 27.9% | 36.3% | 40.9% |
| 0.01 | long | new_chi5 | 29625 | 5.6% | 1648 | 6222 | 26.5% | 34.9% | 42.8% |
| 0.05 | normal | baseline | 11767 | 12.4% | 1458 | 8444 | 17.3% | 18.9% | 35.6% |
| 0.05 | normal | new_default | 21431 | 9.6% | 2053 | 8444 | 24.3% | 26.9% | 42.4% |
| 0.05 | normal | new_chi5 | 17958 | 11.0% | 1970 | 8444 | 23.3% | 25.8% | 44.8% |

The new builder's 2.1x 3-hit points come from both classes (normal 1.8x, long 2.4x); true 3-hit points per event on normal hits rise by 57% (f 0.01) and 41% (f 0.05); the true fraction on normal hits falls from 21.3% to 18.3% (12.4% to 9.6%). Long-hit points are about 5% true.

## Scan design: loose points, SPINE deghosting adjudicates (2026-11-09)

The chi-square cuts (`MaxHitChiSquare`, here fixed at 10; `MaxMythicalChiSquare`, left at its default 25) are not scanned: the point chi-square feeds the Supera/SPINE deghosting.
Goal: find the parameters that raise the recall of true points (normal hits, builder-independent truth triples) and set them as loose as the point volume allows; precision is left to the deghosting.
`scan_hit_fd_loose.json`: 27 points on FD_330003 (8 events), one parameter at a time around `new_default`, plus `baseline` and `loose_all` (all acceptance cuts loosened together, an upper bound for recall and volume):
HitWidthScaleFactor (3.5, 5), DeltaPeakTimeSig (3, 4; HitWidthScaleFactor raised with it, the prefilter must stay at or above the significance cuts), DeltaPeakTimeSigLongHit (3, 5), WirePitchScaleFactor (2.5, 3.5),
RangeNumSigma (4, 5), LongHitsStretchFactor (1, 2.5), PulseHeightFraction (0.2, 0), PHLowSelection (4, 0), MinPHFor2HitPoints (2, 0), MaxTripletsPerPair (8, 32, 64), MaxMythicalPointsPerWire (8, 32, 64).
Run: `/usr/bin/python3 run_hit_scan.py scan_hit_fd_loose.json --dep --no-hit`, then `/usr/bin/python3 scan_rank.py <outdir> --budget 1.5` (ranks by recall; volume relative to `new_default`; true 3-hit points gained per 1000 extra points).
Parameter names checked against the `pset.get` calls in `SnippetHit3DBuilderDUNEFast_tool.cc` (an unknown name in the fcl is silently ignored); a `--debug-config` of a test point shows overrides applied.

## Loose scan results and truth-coverage metric (2026-11-09)

`hitscan_loose` (27 points, FD_330003, events 0 to 7, normal hits, f 0.05, delta 0.2 cm; `scan_rank.py ... --budget 1.5`, tables in `hitscan_loose/{dep_table,cov_table}.txt`). Reference `new_default`: 172881 pts/ev, 2053 true 3-hit/ev, recall 24.3%, any 42.4%.

| point | pts/ev vs ref | true 3h/ev | recall | any | note |
|---|---|---|---|---|---|
| phf_0 (= phl_0) | 1.02 | 2181 (+128) | 25.8% | 44.6% | best trade |
| phf_0.2 | 1.01 | 2126 (+73) | 25.2% | 43.9% | |
| phl_4 | 1.02 | 2108 (+54) | 25.0% | 43.9% | |
| dpts_3 (HWSF 3.5) | 1.27 | 2145 (+92) | 25.4% | 48.8% | dpts_4: same gain at 1.50x |
| wps_2.5 / wps_3.5 | 1.01 / 1.07 | 1770 / 1502 | 21.0% / 17.8% | | worse than default (WPS default 1.9) |
| loose_all | 1.68 | 1878 | 22.2% | 53.9% | worse on every measure; over budget |
| baseline | 0.79 | 1458 | 17.3% | 35.6% | true fraction 12.4% vs 9.6% |

No effect (identical to the digit): hwsf_3.5/5, rns_4/5, trip_8/32/64, myth_8/32/64, mph_0/2, lhs_1. They are not limiting at MaxHitChiSquare 10 (or the setting does not reach the active path). dptsl_3/5 and lhs_2.5 only add long-hit points (not scored; dptsl_5 over budget).

### Recall is not coverage
Recall = recovered truth (U,V,W) triples (built as a 3-hit point with that hit set) / all builder-independent truth triples. One deposit gives many truth triples (charge sharing over adjacent wires, 0.2 cm voxel < wire pitch), so 25% does NOT mean 75% of a trajectory is missing; no absolute ceiling was measured, only comparisons are meaningful.

Coverage (`sp_truth_dep.py`, `--table --cov`, `rerun_cov.sh`): sites = distinct (particle, 0.5 cm cell) of the normal truth triples (position = W voxel of the triple); a site is covered at R if a builder point lies within R cm (any = 2 or 3 hits, p3 = 3 hits, true3 = true 3-hit point). Per-particle coverage for particles with >= 100 sites (34 in the 8 events) at 1 cm. Hit coverage = hits of truth triples that are in a 3-hit point.

| point | true3 @0.5 | true3 @1 | true3 @2 | long-particle median (true3 @1) | hits in 3h pts |
|---|---|---|---|---|---|
| baseline | 79.9% | 95.1% | 98.7% | 95.2% | 95.3% |
| new_default | 82.2% | 95.0% | 98.6% | 95.6% | 95.7% |
| phf_0 | 82.4% | 95.1% | 98.7% | 95.1% | 98.2% |
| wps_2.5 / wps_3.5 | | 85.8% / 70.9% | | 88.9% / 75.8% | |
| loose_all | | 83.5% | | 86.8% | |

Findings: baseline and new builder have the same coverage although recall is 17% vs 24%; no long particle below 50% coverage; parameter changes in the scan move position coverage by at most 0.1 point except the harmful wps and loose_all (cause not investigated); phf_0 raises hit coverage 95.7 to 98.2%.

Caveats: 8 events dominated by a few busy events; "any point" coverage is meaningless in busy events (ghosts cover everything), use true3; the true flag ignores point XYZ (hits share a deposit), so a displaced true point still counts; the truth is partly the same deposits as the metric (circular).

Open (NOT established): whether the gap to 100% at 1 cm (5%) is displaced true points or missing true points. Planned check: for uncovered sites, does a builder 3-hit point exist for one of the site's truth triples (then its distance), plus the 90th/99th percentile of the position error of true points (only the median, 0.28 cm, is known). Open too: whether SPINE deghosting copes with the volume.

Tarball: local build `FD/v10_24_00d00` with dunereco branch `feature/usher_spacepointoptimization` at commit 8a986278 (no uncommitted changes on 2026-11-09); no new tarball has been made by this session.

## Feature study: what separates true from false points (2026-11-09)

Tools: `sp_truth_dep.py --dump` (per-point rows + dmin(f) -> `points.npy`, `points_cols.json`) and `sp_features.py` (numpy only; own histogram GBDT, 400k training points, 120 rounds, depth 4). `new_default` of `hitscan_loose`, 8 FD events, normal hits, label TRUE = common deposit at f 0.05, delta 0.2 cm; train events 0 to 4, test events 5 to 7 (211k points, 4.5% true). Positions not used as features.
Current SpacePoint content (what the error array carries): err[1] = total charge, err[3] = charge asymmetry, chisq; err[0,2,4,5] are free (1,0,0,1) in `Cluster3DDUNE_module.cc` and `SpacePointBuilderDUNE_module.cc`. What Supera actually reads has NOT been checked.

| feature set | AUC | false removed at true eff 90 / 95 / 99% | 3-hit only (90/95/99) | 2-hit only (90/95/99) |
|---|---|---|---|---|
| today (chi2, total charge, asymmetry, n, view mask) | 0.815 | 39 / 22 / 4 | 36 / 22 / 6 | 20 / 9 / 2 |
| + builder (hit sharing degree: all points and 3-hit points; competing points of the same hit pair) | 0.907 | 72 / 52 / 18 | 57 / 42 / 19 | 51 / 33 / 7 |
| + hits (charge and amplitude per view, log ratios and spreads, RMS, peak-time spread) | 0.923 | 77 / 62 / 26 | 64 / 51 / 28 | 63 / 44 / 15 |

Univariate AUC (3-hit): hit sharing degree 0.16 to 0.19 (true points use hits shared with fewer other points), chi2 0.20, peak-time spread 0.27, charge spread 0.39, min hit RMS 0.65 (all as seen from the true class; 0.5 = no information). 2-hit points: sharing degree 0.17, chi2 0.29.
Reading: the hit sharing degree is the largest single gain and exists only inside the builder. Caveats: 3 test events dominated by busy ones; sharing degree is partly an occupancy proxy; the label has about one wire of resolution, so adjacent-wire "false" points are partly correct and the removal fractions are pessimistic; the 99% efficiency end stays weak (26%); no baseline or phf_0 run of the classifier yet; the classifier is not SPINE.

## Tarball for justIN (built 2026-11-09)

`/run/media/usher/Drive2/DUNE/tarballs/dunereco_8a986278_localProducts.tar` (plain uncompressed tar, as justIN requires; sha256 in `dunereco_8a986278_localProducts.tar.sha256`). Contents: `localProducts/` = `FD/v10_24_00d00/localProducts_larsoft_v10_24_00_e26_prof` (dunereco and dunesw v10_24_00d00, e26:prof; `.locks` excluded), the layout the jobscripts expect (`PRODUCTS=$INPUT_TAR_DIR_LOCAL/localProducts:$PRODUCTS`).
Code: dunereco branch `feature/usher_spacepointoptimization`, commit 8a986278 (MaxTripletsPerPair exposed), working tree clean; installed SnippetHit3DBuilderDUNEFast library built 2026-11-03 07:09, source 07:06, commit 07:10. FD only (no VD localProducts here).
Tested: extracted into a scratch dir, `PRODUCTS` set as in `reco_tarball.jobscript`, `setup dunesw v10_24_00d00 -q e26:prof` picks dunereco and dunesw from the extracted path (`ups active`), `lar -c sp_hit_dune10kt_1x2x6.fcl -n 1` exits 0 and writes sp_art.root.
Not done: upload to cvmfs (needs a DUNE gpvm; the resulting hash goes into `tarfile_dir` of the configs). Size limit of the upload not checked.

## SpacePointBuilderDUNEFeat: hit sharing features in the SpacePoint (2026-11-09)

What Supera takes from the points (read from `Supera/SuperaSpacePoint.cxx`, `SuperaCluster3D.cxx`, `SuperaTrue2RecoVoxel3D.cxx`; the workshop chain is standard_supera -> supera_dunefdhd_mc.fcl, StoreWireInfo true, DropOutput hit_amp/hit_rms/hit_mult; the include chain was read but not run): charge = ErrXYZ()[1] (range cut RecoChargeRange), chisq per voxel, nhits (Assns), occupancy (points per voxel), cryo/tpc, per-plane hit_charge and hit_time. ErrXYZ()[3] (asymmetry) is read but its output is commented out; ErrXYZ()[0] is read by SuperaCluster3D as a voxel value (keep 1); ErrXYZ()[2], [4], [5] are not read by anything found. With several points in a voxel Supera keeps one (more hits first, then larger charge).

Ablation (`sp_features.py --ablate`, new_default, test events 5 to 7): Supera-like inputs (chi2, total charge, n, per-plane charge, peak-time spread, charge ratios) AUC 0.864, false removed at true eff 90/95/99% = 59/43/17%; + deg_mean, deg3_max, pair_max: 0.916, 75/59/22%; + all builder features: 0.915, 74/58/21% (the three capture all of it); 3-hit only 47/31/7% -> 60/45/21%, 2-hit only 45/31/10% -> 59/39/13%. Occupancy (points per voxel) is not in this study.

New module `Cluster3D/SpacePointBuilderDUNEFeat_module.cc` (copy of SpacePointBuilderDUNE, registered in `Cluster3D/CMakeLists.txt`; the original module is untouched; `WriteFeatures: false` reproduces its output): ErrXYZ()[2] = mean over the point's hits of the number of points using the hit; [4] = max over the hits of the number of 3-hit points using the hit; [5] = max over the hit pairs of the number of points containing both. A hit is identified by (channel, start, end, peak time rounded to 0.1 tick), not by address: the builder output contains exact duplicate copies of the same hit (event 0: 15712 output hits, 12558 distinct keys; 3036 keys twice, 59 three times; identical charge/amplitude/RMS/DOF), so counting by address gives lower degrees (mean 128.6 vs 130.5, up to 198 off per point).
Test (fcl `DUNESpineWorkshop2026/fhicl/sp_hit_dune10kt_1x2x6_feat.fcl` + MaxHitChiSquare 10, events 0 and 1 of FD_330003): 276557 and 122988 points, identical to the new_default output; XYZ, charge, asymmetry and slot 0 unchanged; slots 2, 4, 5 equal the offline features of `sp_features.py` exactly (max diff 0).
Build: `ninja -j6 install` in `build_slf7.x86_64` (after `mrbsetenv`); the added CMake target made the first build rebuild 324 targets, installed into the local products. NOT in `tarballs/dunereco_8a986278_localProducts.tar` (made before; that tar still has the old libraries); the dunereco working tree now has uncommitted changes (the new module and CMakeLists.txt).
Open: Supera does not read slots 2, 4, 5 yet (needs new voxel sets in SuperaSpacePoint); not run on VD; features not tested with SPINE; the duplicate hit copies in the builder output are unexplained (not investigated why, and what they cost Supera).

### Correction: the "duplicate hits" are wrapped-wire copies, by design (2026-11-09)
Both builders (baseline `SnippetHit3DBuilderDUNE` and the Fast tool) create one new recob::Hit per distinct 2D hit object in `CreateNewRecobHitCollection`, stamped with the "correct WireID". Checked on events 0 and 1 of FD_330003: the input gaushit collection has no duplicate (channel, start, end, peak) keys; the builder outputs do (event 0: baseline 3120 extra copies of 15673 hits = 19.9%, new_default 3154 of 15712 = 20.1%; event 1: 6.1% and 6.3%). All duplicate groups are induction hits (views 0 and 1; none in view 2), no group repeats a WireID, the members are mostly in different TPCs (2911 of 3062 baseline groups) and some groups have 3 copies in one APA: the same channel pulse assigned to each candidate wire segment of the wrapped induction wires. So these are wire-segment ambiguity copies, not a bug. Neither builder produces duplicate space points: no point repeats another point's hit set (0 in both builders, events 0 and 1).
Consequence for the studies: hit identity by (channel, start, end, peak) is the physical pulse; the truth label (hits share a deposit) does not look at the point XYZ, so a point built on the wrong wire segment would still be labelled true. Position error of the points labelled true (`sp_truth_dep.py`, f 0.05, delta 0.2, normal hits, 8 events):
| builder | 3-hit median / p90 / p99 (cm) | 3-hit > 1 cm | 2-hit median / p90 / p99 (cm) | 2-hit > 1 cm |
|---|---|---|---|---|
| baseline | 0.30 / 0.57 / 1.05 | 1.2% | 0.61 / 1.16 / 1.90 | 16.7% |
| new_default | 0.31 / 0.61 / 1.23 | 1.9% | 0.60 / 1.22 / 2.04 | 19.2% |
So at most about 2% of the true 3-hit points sit far from their deposit (wrong wire segment or similar); for the true 2-hit points 17 to 19% are off by more than 1 cm, so their label is noisier. (Not separated: how many of the >1 cm points are wrong-segment aliases; the far-off tail is only to 2 cm at p99, so large offsets like another TPC are rare.) This also answers the earlier open question about the position error tail of true points.

## Timing: baseline vs new builder vs Feat module (2026-11-09)
Sequential runs, laptop (SL7 container, local build), 8 events of FD_330003, builder only (`sp_hit_*` fcls, no Supera, MaxHitChiSquare 10), whole `lar` job incl. startup, reading and writing sp_art.root; each variant twice. (The scan's own `time.log` files were taken with 6 jobs in parallel and are not clean.)
| variant | user CPU (s) | max RSS (MB) | event 3 (542k points in the baseline run), s | sum events 1..7 (s) |
|---|---|---|---|---|
| baseline (Cluster3DDUNE + SnippetHit3DBuilderDUNE) | 35.1 / 35.3 | 1700 to 1750 | 13 / 13 | 19 / 19 |
| new (SpacePointBuilderDUNE + Fast tool) | 38.0 / 38.1 | 1769 | 14 / 14 | 22 / 23 |
| new + SpacePointBuilderDUNEFeat | 40.0 / 40.0 | 1745 to 1786 | 15 / 16 | 24 / 24 |
New builder about 8% more CPU than the baseline (the baseline makes fewer points: 137k vs 173k per event), the Feat module a further 5%. The new builder is not faster in this test. Event start times are logged to 1 s, there is no per-module breakdown (TimeTracker output not retrieved), so builder-only times are not isolated.

## Status 2026-11-10 and first justIN test round

Where we stand: new builder is not faster (+8% CPU) and has equal coverage (about 95%) to the baseline; the Feat module (ErrXYZ[2,4,5]) has only an offline classifier result (AUC 0.864 to 0.916) and Supera ignores those slots. Open: Supera voxel-efficiency comparison, copy-level vs pulse-level degree, SPINE-side test, displaced-vs-missing check. Nothing committed in dunereco (Feat module uncommitted).

justIN tarball `/cvmfs/fifeuser1.opensciencegrid.org/sw/dune/b1e047352838e58c7fb1e808920974ee7a7dcb1d`: dunesw and dunereco v10_24_00d00 (e26:prof), dunereco commit 8a986278; the SpacePointBuilderDUNE module library is byte-identical to `tarballs/dunereco_8a986278_localProducts.tar`. No Feat module in it.
Configs (tarfile_dir set to it, 1000 events each = jobs x NEVENTS):
- FD HD, new builder: `DUNESpineWorkshop2026/mvpmpr_2hitSP_testcode_config.json` (20 x 50, RUN_BASE 340000; reco fcl `standard_mythical_supera_dune10kt_1x2x6.fcl`)
- FD VD, new builder: `DUNEVD/mpvmpr_2hitSP_testcode_config.json` (10 x 100, RUN_BASE 030000; reco fcl `standard_supera_dunevd10kt_1x8x6_3view_30deg.fcl`)
- Baseline counterparts (`mvpmpr_2hitSP_baseline_config.json`, `mpvmpr_2hitSP_baseline_config.json`) still point at the old tarballs and are 10 x 20 events; not changed.
Fhicl comes from the bundles on GitHub main (identical to the repo fhicl dirs checked 2026-11-10). The old VD tarball (fifeuser2 da6832...) was not visible from cvmfs here, so it was not compared with the new one.

## Default builder reset to the original tool (2026-11-10)

The Fast tool has not proven itself (no speed gain, equal coverage), so the default space point build in the production fcls is now `SpacePointBuilderDUNE` (module: space points only, no clustering/PR products) running the ORIGINAL `SnippetHit3DBuilderDUNE` tool with `MaxHitChiSquare: 10`. Done in `DUNESpineWorkshop2026/fhicl/workflow_reco_dune10kt.fcl` and `DUNEVD/fhicl/workflow_reco_dunevd10kt.fcl` (prolog entry `standard_spacepointbuilderdune_origtool`; dunereco and the tarball are unchanged, `standard_spacepointbuilderdune` in dunereco still defaults to Fast). Both bundles `bundles/fhicl_bundle.tgz`, `fhicl_vd_bundle.tgz` rebuilt locally, differing from HEAD only in that file; NOT pushed (justIN reads them from GitHub main). Checked with `--debug-config` (all four standard/baseline top-level fcls) and a 1-event `sp_hit_dune10kt_1x2x6.fcl` run (rc 0).
Note: the earlier "testcode" configuration (new module + Fast tool) ran with the tool default `MaxHitChiSquare: 6`, while the baseline fcls use 10; the scan used 10 for both. Any justIN sample made before this change with the testcode configs used chi2 6.
