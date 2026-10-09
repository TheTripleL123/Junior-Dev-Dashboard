"""Prune Junior Dev runs older than RETENTION_DAYS from AllTestRuns/.

Run folders are dated from their metadata.json "timestamp" field, falling back to
the DD-MM-YYYY_HH-MM-SS stamp in the folder name. A folder whose date can't be
read is kept - never guess a run into the trash.

Retention matches the Google Drive cleanup window (daily_ci_clean.yaml in underdogs):
once Drive drops a run, its drive_link is dead, so keeping the row is misleading.

Unlike the Bots / Scene Test dashboards there is no performance history to keep -
a Junior Dev run is a one-off task, not a point on a trend.
"""

import json
import os
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone

RUNS_DIR = "AllTestRuns"
RETENTION_DAYS = int(os.environ.get("RETENTION_DAYS", "10"))

# DD-MM-YYYY_HH-MM-SS, also tolerating DD-MM-YY and a missing time part.
STAMP = re.compile(r"(\d{1,2})-(\d{1,2})-(\d{2,4})(?:[_ ](\d{1,2})-(\d{1,2})-(\d{1,2}))?")


def parse_stamp(text):
    m = STAMP.search(text or "")
    if not m:
        return None
    day, month, year, hour, minute, sec = m.groups()
    year = int(year)
    if year < 100:
        year += 2000
    try:
        return datetime(year, int(month), int(day),
                        int(hour or 0), int(minute or 0), int(sec or 0),
                        tzinfo=timezone.utc)
    except ValueError:
        return None


def run_date(folder_path, folder_name):
    """metadata.json is authoritative; the folder name is the fallback."""
    meta_path = os.path.join(folder_path, "metadata.json")
    if os.path.isfile(meta_path):
        try:
            with open(meta_path, encoding="utf-8") as f:
                parsed = parse_stamp(json.load(f).get("timestamp"))
            if parsed:
                return parsed
        except Exception as e:
            print(f"  WARNING: could not read {meta_path}: {e}")
    return parse_stamp(folder_name)


def main():
    if not os.path.isdir(RUNS_DIR):
        print(f"No {RUNS_DIR}/ directory - nothing to prune.")
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    print(f"Retention: {RETENTION_DAYS} days (cutoff {cutoff:%Y-%m-%d %H:%M} UTC)")

    deleted = 0
    for name in sorted(os.listdir(RUNS_DIR)):
        path = os.path.join(RUNS_DIR, name)
        if not os.path.isdir(path):
            continue
        date = run_date(path, name)
        if date is None:
            print(f"  KEEP (undated) {name}")
            continue
        if date >= cutoff:
            print(f"  keep  {date:%Y-%m-%d}  {name}")
            continue
        shutil.rmtree(path)
        deleted += 1
        print(f"  PRUNE {date:%Y-%m-%d}  {name}")

    print(f"Pruned {deleted} run(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
