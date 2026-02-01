#!/usr/bin/env python3
import re
import csv
import time
from   pathlib import Path
import requests
import pandas as pd

#
# The idea here is to plot status for jobs in a given workflow for a given stage. 
# We start by downloading the lists of jobsub IDs that we get from the following 
# justin command:
#
#    justin show-jobs --workflow-id wfid --stage-id stageID | awk '{print $1}' > jobids.txt
#
# Note that this will download into a single file all jobs in the workflow, for the given stageID. 
# This command needs to be executed once for each stage (as far as I know) so it is good
# to postfix your "jobids.txt" file with the stage id for later reference
#

BASE = "https://dunejustin.fnal.gov/dashboard/?method=show-job&jobsub_id={jobid}"

# Matches things like:
# Stage ID
# Job State finished
# Exit code 0
# Real time 00:21:34
# CPU time 00:20:58
# Max RSS bytes 2147483648
STAGE_RE = re.compile(r"Stage\s+ID\s+(-?\d+)", re.IGNORECASE)
JOB_RE   = re.compile(r"Job\s+state\s+(\w+)", re.IGNORECASE)
EXIT_RE  = re.compile(r"Exit\s+code\s+(-?\d+)", re.IGNORECASE)
WALL_RE  = re.compile(r"Real\s+time\s+(.+?)\s+CPU\s+time", re.IGNORECASE)
CPU_RE   = re.compile(r"CPU\s+time\s+(.+?)\s+Max\s+RSS", re.IGNORECASE)
RSS_RE   = re.compile(r"Max\s+RSS\s+bytes\s+(.+?)\s+Outputting", re.IGNORECASE)

# Jobscript Exit code 0 Real time 0m (22s) CPU time 0m (19s = 86%) Max RSS bytes 587616256 (560 MiB)

TAG_RE   = re.compile(r"<[^>]+>")

def hms_to_seconds(hms: str) -> int:
    h, m, s = hms.split(":")
    return int(h) * 3600 + int(m) * 60 + int(s)

def html_to_text(html: str) -> str:
    # crude but effective: strip tags, collapse whitespace
    text = TAG_RE.sub(" ", html)
    return " ".join(text.split())

def fetch_job(session: requests.Session, jobid: str, timeout: int = 30, retries: int = 3) -> dict:
    url = BASE.format(jobid=jobid)
    last_err = None
    fields = {}  # <-- add this
    
    for attempt in range(1, retries + 1):
        try:
            r = session.get(url, timeout=timeout)
            r.raise_for_status()
            text = html_to_text(r.text)
    
            stage = STAGE_RE.search(text)
            if stage:
                stageID = int(stage.group(1))
                fields["stageID"] = stageID
    
            job_state = JOB_RE.search(text)
            if job_state:
                fields["jobState"] = job_state.group(1)
    
            if job_state and "finished" in job_state.group(1):
                exit_m = EXIT_RE.search(text)
                wall_m = WALL_RE.search(text)
                cpu_m  = CPU_RE.search(text)
                rss_m  = RSS_RE.search(text)
    
                fields["exit"] = int(exit_m.group(1))
                fields["wall"] = wall_m.group(1).strip()
                fields["cpu"]  = cpu_m.group(1).strip()
                fields["rss"]  = rss_m.group(1).strip()
    
                break
    
        except Exception as e:
            print("ERROR:", repr(e))  # <-- add this
            time.sleep(0.5 * attempt)

    return fields

WALL_SECS_RE = re.compile(r"\((\d+)s\)")          # matches "(22s)"
CPU_SECS_RE  = re.compile(r"\((\d+)s")            # matches "(19s = 86%)" too
RSS_BYTES_RE = re.compile(r"(\d+)")               # first integer

def parse_seconds(s: str) -> int | None:
    if not s:
        return None
    m = WALL_SECS_RE.search(s) or CPU_SECS_RE.search(s)
    return int(m.group(1)) if m else None

def parse_rss_bytes(s: str) -> int | None:
    if not s:
        return None
    m = RSS_BYTES_RE.search(s)
    return int(m.group(1)) if m else None

SECONDS_RE = re.compile(r"\((\d+)s\)")
FIRST_INT_RE = re.compile(r"(\d+)")
CPU_DETAIL_RE = re.compile(
    r"\(\s*(?P<seconds>\d+)s\s*=\s*(?P<percent>\d+)%\s*\)",
    re.IGNORECASE
)

def parse_seconds_from_parens(s: str):
    """Extract seconds from '(123s)' anywhere in the string."""
    if not s:
        return None
    m = SECONDS_RE.search(s)
    return int(m.group(1)) if m else None

def parse_cpu_detail(s: str):
    """
    Parse '(19s = 86%)' from a CPU time string.
    Returns (cpu_seconds, cpu_fraction) or (None, None).
    """
    if not s:
        return None, None

    m = CPU_DETAIL_RE.search(s)
    if not m:
        return None, None

    cpu_s = int(m.group("seconds"))
    cpu_frac = int(m.group("percent")) / 100.0
    return cpu_s, cpu_frac

def parse_first_int(s: str):
    """Extract the first integer found in the string."""
    if not s:
        return None
    m = FIRST_INT_RE.search(s)
    return int(m.group(1)) if m else None

def getStageInfo(jobIdsFile, stageID: int = 1):
    jobids_path = Path(jobIdsFile)
    print("Input file:", jobIdsFile, ", path:", jobids_path)
    if not jobids_path.exists():
        raise SystemExit("Missing jobids.txt. Create it with: justin show-jobs --workflow-id 12080 | awk '{print $1}' > jobids.txt")

    jobids = [line.strip() for line in jobids_path.read_text().splitlines() if line.strip()]

    out_csv = Path("workflow12080_stats.csv")
    fieldnames = ["job", "stageID", "jobState", "exit", "wall_s", "cpu_s", "maxrss_bytes"]

    with requests.Session() as session, out_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()

        for i, jobid in enumerate(jobids, 1):
            fields = fetch_job(session, jobid)   # returns your dict

            #Only looking at one stage at a time
            if fields["stageID"] != stageID:
                continue

            # Build a row with exactly the CSV columns
            row_out = {
                "job": jobid,
                "stageID": fields.get("stageID"),
                "jobState": fields.get("jobState"),
                "exit": fields.get("exit"),
                # If your parser stores raw strings like "0m (22s)" / "5876... (560 MiB)"
                "wall_s": parse_seconds(fields.get("wall")),
                "cpu_s":  parse_seconds(fields.get("cpu")),
                "maxrss_bytes": parse_rss_bytes(fields.get("rss")),
            }

            w.writerow(row_out)

            if i % 50 == 0:
                print(f"Processed {i}/{len(jobids)}")

    print(f"Wrote {out_csv}")


def getStageInfo_df(jobIdsFile):
    jobids_path = Path(jobIdsFile)
    print("Input file:", jobIdsFile, ", path:", jobids_path)
    if not jobids_path.exists():
        raise SystemExit("Missing jobids.txt. Create it with: justin show-jobs --workflow-id 12080 | awk '{print $1}' > jobids.txt")

    jobids = [line.strip() for line in jobids_path.read_text().splitlines() if line.strip()]
    
    rows = []
    with requests.Session() as session:
        print("Input job id file has",len(jobids),"entries")
        for i, jobid in enumerate(jobids, 1):
            fields = fetch_job(session, jobid)
    
            cpu_raw = fields.get("cpu") or fields.get("cpu_m")
    
            cpu_s, cpu_frac = parse_cpu_detail(cpu_raw)
    
            row = {
                "job": jobid,
                "stageID": fields.get("stageID"),
                "jobState": fields.get("jobState"),
                "exit": fields.get("exit"),
    
                "wall_raw": fields.get("wall") or fields.get("wall_s"),
                "cpu_raw": cpu_raw,
                "rss_raw": fields.get("rss") or fields.get("rss_m"),
    
                # numeric columns
                "wall_s": parse_seconds_from_parens(fields.get("wall") or fields.get("wall_s")),
                "cpu_s": cpu_s,
                "cpu_frac": cpu_frac,
                "maxrss_bytes": parse_first_int(fields.get("rss") or fields.get("rss_m")),
            }
    
            rows.append(row)

            if i % 50 == 0:
                print(f"Processed {i}/{len(jobids)}")

    df = pd.DataFrame(rows)

    # Optional: enforce numeric dtypes (nullable Int64 handles None cleanly)
    for col in ["stageID", "exit", "wall_s", "cpu_s", "maxrss_bytes"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    return df


def getAllStageInfo_df(jobIDsFiles,path=""):
    print("We have",len(jobIDsFiles),"to process with path:",path)
    
    dfList = []

    for jobIDsFile in jobIDsFiles:
        print("Processing:",jobIDsFile)

        dfList.append(getStageInfo_df(path+jobIDsFile))

    return pd.concat(dfList,ignore_index=True)