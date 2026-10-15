"""Create a small, rating-balanced smoke-test CSV from the Kaggle archive."""

import argparse
import csv
import io
import json
from collections import Counter
from pathlib import Path
from zipfile import ZipFile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--per-score", type=int, default=2)
    args = parser.parse_args()
    if args.per_score < 1:
        parser.error("--per-score must be positive")

    counts: Counter[int] = Counter()
    rows = []
    with ZipFile(args.archive) as archive:
        names = [n for n in archive.namelist() if Path(n).name == "Reviews.csv"]
        if len(names) != 1:
            raise ValueError("Archive must contain exactly one Reviews.csv")
        with archive.open(names[0]) as source:
            for row in csv.DictReader(io.TextIOWrapper(source, encoding="utf-8-sig")):
                score = int(row["Score"])
                text = row["Text"].strip()
                if score not in range(1, 6) or not text or len(text) > 20000:
                    continue
                if counts[score] >= args.per_score:
                    continue
                rows.append({"Id": row["Id"], "Text": text, "Score": score})
                counts[score] += 1
                if len(rows) == 5 * args.per_score:
                    break
    if len(rows) != 5 * args.per_score:
        raise ValueError("Not enough valid reviews for every rating")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Refuse to overwrite a dataset prepared by the user.
    with args.output.open("x", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=["Id", "Text", "Score"])
        writer.writeheader()
        writer.writerows(rows)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "rows": len(rows),
                "score_counts": dict(sorted(counts.items())),
            }
        )
    )


if __name__ == "__main__":
    main()
