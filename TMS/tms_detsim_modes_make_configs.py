#!/usr/bin/env python3
"""Write the justIN workflow JSON files for the detector-simulation comparison (legacy, new, timing 1 PE, timing 3 PE).
Usage: tms_detsim_modes_make_configs.py <cvmfs tarball dir> [version tag, default v01] [output dir]
Every workflow is two stages: ConvertToTMSTree in one DETSIM_MODE (tms_detsim_modes.jobscript), then Tracking_Validation."""
import json, os, sys

tar = sys.argv[1]
ver = sys.argv[2] if len(sys.argv) > 2 else "v01"
out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "detsim_modes_configs")
os.makedirs(out, exist_ok=True)
MODES = {  # name: env of stage 1
    "legacy": {"DETSIM_MODE": "legacy"},
    "new": {"DETSIM_MODE": "new"},
    "timing_thr1": {"DETSIM_MODE": "timing", "DETSIM_THRESHOLD": "1.0"},
    "timing_thr3": {"DETSIM_MODE": "timing", "DETSIM_THRESHOLD": "3.0"},
}
for name, env in MODES.items():
    env = dict(env, TMS_PRODUCTION_TAG="DetSim_%s_%s" % (name, ver))
    cfg = {
        "workflow": {"description": "TMS MiniProdN5p3 FHC detector-simulation comparison, mode %s (two stage)" % name,
                     "mql": "files from neardet-lar-tms-sand:MiniProdN5p3_NDComplex_FHC_spill_full_sanddrift"},
        "defaults": {"repo": "SFBayLaser/dune-justin", "ref": "main", "lifetime_days": 4, "max_distance": 60,
                     "limit_sites": False, "tarfile_dir": tar},
        "stages": [
            {"id": 1, "jobscript": "TMS/tms_detsim_modes.jobscript", "wall_seconds": 28800, "rss_mib": 4000,
             "lifetime_days": 14, "env": env, "output_patterns": ["*_Readout.root", "*_convert.log"],
             "output_pattern_next_stage": "*_RecoCandidates.root"},
            {"id": 2, "jobscript": "TMS/tms_validation.jobscript", "wall_seconds": 14400, "rss_mib": 8000,
             "lifetime_days": 14, "output_patterns": ["*_validation_legacy.root", "*_validation_cluster3d.root", "*_validation.log"]},
        ]}
    p = os.path.join(out, "tms_detsim_%s_%s_config.json" % (name, ver))
    json.dump(cfg, open(p, "w"), indent=2); open(p, "a").write("\n"); print(p)
