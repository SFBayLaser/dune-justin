#!/usr/bin/env python3
"""Write one two-stage justIN workflow config per bad channel set (the bad channel scan).

Stage 1 (tms_badchannels.jobscript) converts each MiniProdN5p3 spill with the bad channel list BAD_SET
applied in the decoder; only its log is kept, the RecoCandidates file goes to stage 2. Stage 2 is the usual
tms_validation.jobscript (Tracking_Validation, legacy and Cluster3D), whose small histogram files are the
result of the job.

The lists f<percent>_s<seed> (f00 = none) are the ones in the tarball's config/justin/badchannels/, made by
scripts/BadChannels/make_bad_channel_lists.py in dune-tms. The tag in the output names is
TMSReco_BadCh_<set>_<version>, so the set can be read off a file name.

Usage: tms_badchannels_make_configs.py TARFILE_DIR [--sets f00 f05_s1 ...] [--version v01] [--limit N] [--outdir DIR] [--draw]
  TARFILE_DIR  the cvmfs directory justin-cvmfs-upload printed for the tarball
               current: /cvmfs/fifeuser4.opensciencegrid.org/sw/dune/bfe303fd3497a673c2ba2409ce941313629f5f7a
  --limit N    only the first N files of the dataset (a test)
"""
import argparse
import json
import os

DEFAULT_SETS = ["f00"] + [f"f{f:02d}_s{s}" for s in (1, 2, 3) for f in (5, 10, 15, 20, 25)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tarfile_dir")
    ap.add_argument("--sets", nargs="+", default=DEFAULT_SETS)
    ap.add_argument("--version", default="v01")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--outdir", default="badchannels_configs")
    ap.add_argument("--draw", action="store_true", help="stage 2 with the event displays (tms_validation.jobscript)")
    args = ap.parse_args()

    mql = "files from neardet-lar-tms-sand:MiniProdN5p3_NDComplex_FHC_spill_full_sanddrift"
    if args.limit > 0:
        mql += f" limit {args.limit}"
    os.makedirs(args.outdir, exist_ok=True)
    for name in args.sets:
        config = {
            "workflow": {
                "description": f"TMS bad channel scan, set {name}: spill processing + validation (two stage)",
                "mql": mql,
            },
            "defaults": {
                "repo": "SFBayLaser/dune-justin",
                "ref": "main",
                "lifetime_days": 4,
                "max_distance": 60,
                "limit_sites": False,
                "tarfile_dir": args.tarfile_dir,
            },
            "stages": [
                {
                    "id": 1,
                    "jobscript": "TMS/tms_badchannels.jobscript",
                    "wall_seconds": 28800,
                    "rss_mib": 4000,
                    "lifetime_days": 14,
                    "env": {"TMS_PRODUCTION_TAG": f"TMSReco_BadCh_{name}_{args.version}", "BAD_SET": name},
                    "output_patterns": ["*_convert.log"],
                    "output_pattern_next_stage": "*_RecoCandidates.root",
                },
                {
                    "id": 2,
                    "jobscript": "TMS/tms_validation.jobscript" if args.draw else "TMS/tms_validation_nodraw.jobscript",
                    "wall_seconds": 14400,
                    "rss_mib": 8000,
                    "lifetime_days": 14,
                    "output_patterns": ["*_validation_legacy.root", "*_validation_cluster3d.root", "*_validation.log"],
                },
            ],
        }
        path = os.path.join(args.outdir, f"tms_badchannels_{name}_config.json")
        with open(path, "w") as f:
            json.dump(config, f, indent=2)
            f.write("\n")
        print(path)


if __name__ == "__main__":
    main()
