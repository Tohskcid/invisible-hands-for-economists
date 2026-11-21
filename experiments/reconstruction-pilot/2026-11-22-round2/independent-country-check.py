"""Independent country-data check. Run with python3 check.py."""
import csv
import hashlib
import io
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MEASURES = ("schooling_pct", "investment_pct", "working_age_growth_pct")


def pearson(x, y):
    # Centered cross-products scaled by n. All inputs are decimal percentages.
    n = len(x)
    cross = n * sum(a * b for a, b in zip(x, y, strict=True)) - sum(x) * sum(y)
    xx = n * sum(a * a for a in x) - sum(x) ** 2
    yy = n * sum(b * b for b in y) - sum(y) ** 2
    return float(cross / (xx * yy).sqrt())


def main():
    data = (ROOT / "inputs/input-1.csv").read_bytes()
    dictionary = (ROOT / "inputs/input-2.txt").read_text()
    reader = csv.DictReader(io.StringIO(data.decode("utf-8")))
    rows = list(reader)
    assert all(name in dictionary for name in reader.fieldnames)
    assert len(rows) == len({row["country"] for row in rows}) == 121
    flags = ("sample_nonoil", "sample_intermediate", "sample_oecd")
    assert all(row[key] in {"0", "1"} for row in rows for key in flags)
    assert all(row[flags[0]] >= row[flags[1]] >= row[flags[2]] for row in rows)
    assert [sum(row[k] == "1" for row in rows) for k in flags] == [98, 75, 22]

    selected = [row for row in rows if row["sample_intermediate"] == "1"]
    complete = [row for row in selected if all(row[k] != "" for k in MEASURES)]
    assert len(complete) == len(selected)
    school, invest, growth = ([Decimal(row[k]) for row in complete] for k in MEASURES)
    result = dict(input_sha256=hashlib.sha256(data).hexdigest(), n=len(complete),
                  schooling_investment=pearson(school, invest),
                  schooling_population=pearson(school, growth),
                  # Visually transcribed from the first paragraph of printed p. 420.
                  printed_investment=0.59, printed_population=-0.38)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
