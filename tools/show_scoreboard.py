"""Build a relative scoreboard from saved comparison results."""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--direction", choices=("lower", "higher"), required=True)
    parser.add_argument("--csv", type=Path, default=ROOT / "reports" / "scoreboard.csv")
    args = parser.parse_args()
    observations = defaultdict(dict)
    for cases_path in sorted((ROOT / "reports" / "experiments").glob("*/cases.csv")):
        summary_path = cases_path.with_name("summary.json")
        if not summary_path.exists():
            continue
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary.get("score_direction") != args.direction:
            continue
        with cases_path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                for side in ("baseline", "candidate"):
                    if row[f"{side}_ok"].lower() != "true":
                        continue
                    solver = summary[side]
                    case = row["case"]
                    score = float(row[f"{side}_score"])
                    old = observations[solver].get(case)
                    if old is None or (score < old if args.direction == "lower" else score > old):
                        observations[solver][case] = score
    if not observations:
        parser.error("no matching successful observations")
    cases = sorted({case for results in observations.values() for case in results})
    best = {case: (min if args.direction == "lower" else max)(results[case] for results in observations.values() if case in results) for case in cases}
    rows = []
    for solver, results in observations.items():
        if len(results) != len(cases):
            continue
        points = 0.0
        for case in cases:
            reference, score = best[case], results[case]
            if reference == score:
                points += 100
            elif args.direction == "lower" and score > 0:
                points += 100 * reference / score
            elif args.direction == "higher" and reference > 0:
                points += 100 * score / reference
        rows.append({"solver": solver, "points": round(points, 3), "cases": len(cases)})
    rows.sort(key=lambda row: (-row["points"], row["solver"]))
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("rank", "solver", "points", "cases"))
        writer.writeheader()
        for rank, row in enumerate(rows, 1):
            writer.writerow({"rank": rank, **row})
            print(f"{rank:>3} {row['solver']:<28} {row['points']:>10.3f} / {100 * len(cases)}")
    print(f"Saved: {args.csv}")


if __name__ == "__main__":
    main()
