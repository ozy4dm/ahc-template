"""Run a fixed case set against two solvers and an official scorer.

The command strings in config.json use {input} and {output} placeholders. Commands
are argument arrays so paths and arguments are passed without shell evaluation.
"""

import argparse
import csv
import json
import re
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def command(parts, input_path, output_path):
    args = [str(part).replace("{input}", str(input_path)).replace("{output}", str(output_path)) for part in parts]
    # Resolve a relative executable path against the repository root. Windows cannot start
    # a relative path written with "/" (e.g. target/release/solver.exe) on its own.
    executable = ROOT / args[0]
    if not Path(args[0]).is_absolute() and executable.is_file():
        args[0] = str(executable)
    return args


def run_solver(parts, input_path, output_path, timeout):
    started = time.perf_counter()
    try:
        with input_path.open("rb") as source, output_path.open("wb") as target:
            result = subprocess.run(parts, stdin=source, stdout=target, stderr=subprocess.PIPE, timeout=timeout, cwd=ROOT)
        return result.returncode, False, round((time.perf_counter() - started) * 1000, 3), result.stderr.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        return None, True, round((time.perf_counter() - started) * 1000, 3), "time limit exceeded"


def score(parts, pattern, input_path, output_path, timeout):
    try:
        result = subprocess.run(command(parts, input_path, output_path), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, cwd=ROOT)
    except subprocess.TimeoutExpired:
        return None, "scorer time limit exceeded"
    message = (result.stdout + "\n" + result.stderr).strip()
    if result.returncode != 0:
        return None, f"scorer exit {result.returncode}: {message[:300]}"
    match = re.search(pattern, message)
    if not match:
        return None, f"score not found: {message[:300]}"
    return float(match.group(1)), ""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", help="experiment ID, e.g. EXP-001")
    parser.add_argument("baseline", help="solver command key in config.json")
    parser.add_argument("candidate", help="solver command key in config.json")
    parser.add_argument("--config", type=Path, default=ROOT / "config.json")
    args = parser.parse_args()
    if not re.fullmatch(r"EXP-\d{3,}", args.experiment):
        parser.error("experiment must look like EXP-001")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    for key in (args.baseline, args.candidate):
        if key not in config["solvers"]:
            parser.error(f"unknown solver: {key}")
    direction = config["score_direction"]
    if direction not in ("lower", "higher"):
        parser.error("score_direction must be lower or higher")
    inputs = sorted(ROOT.glob(config["input_glob"]))
    if not inputs:
        parser.error("no input files matched input_glob")
    report_dir = ROOT / "reports" / "experiments" / args.experiment
    if report_dir.exists():
        parser.error(f"report already exists: {report_dir}")
    report_dir.mkdir(parents=True)
    rows = []
    try:
        with tempfile.TemporaryDirectory(dir=report_dir) as temp:
            temp_path = Path(temp)
            for input_path in inputs:
                row = {"case": input_path.stem}
                for side, key in (("baseline", args.baseline), ("candidate", args.candidate)):
                    output = temp_path / f"{input_path.stem}_{side}.txt"
                    code, timed_out, elapsed, error = run_solver(command(config["solvers"][key], input_path, output), input_path, output, config["time_limit_seconds"])
                    value, score_error = (None, error[:300]) if timed_out or code != 0 else score(config["scorer"], config["score_pattern"], input_path, output, config.get("scorer_time_limit_seconds", 30))
                    row[f"{side}_score"] = value
                    row[f"{side}_ok"] = value is not None
                    row[f"{side}_ms"] = elapsed
                    row[f"{side}_timeout"] = timed_out
                    row[f"{side}_error"] = score_error if value is None else ""
                if row["baseline_ok"] and row["candidate_ok"]:
                    row["delta"] = row["candidate_score"] - row["baseline_score"]
                else:
                    row["delta"] = None
                rows.append(row)
                print(f"{input_path.name}: baseline={row['baseline_score']} candidate={row['candidate_score']}")
    except BaseException:
        # Preserve completed observations if a later case fails unexpectedly.
        if rows:
            write_csv(report_dir / "cases.partial.csv", rows)
        raise
    write_csv(report_dir / "cases.csv", rows)
    paired = [row for row in rows if row["delta"] is not None]
    improvements = [row for row in paired if (row["delta"] < 0 if direction == "lower" else row["delta"] > 0)]
    summary = {
        "experiment": args.experiment,
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "baseline": args.baseline,
        "candidate": args.candidate,
        "score_direction": direction,
        "case_count": len(rows),
        "success_count": len(paired),
        "failure_count": len(rows) - len(paired),
        "improved": len(improvements),
        "equal": sum(row["delta"] == 0 for row in paired),
        "worse": len(paired) - len(improvements) - sum(row["delta"] == 0 for row in paired),
    }
    (report_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
