"""Descriptive Beveridge-curve comparison from frozen, real BLS observations."""

import csv
import hashlib
import json
from pathlib import Path
from statistics import mean, median

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SERIES = {"LNS14000000": "unemployment", "JTS000000000000000JOR": "openings"}


def load():
    by_date = {}
    for path in sorted(RAW.glob("bls-*.json")):
        response = json.loads(path.read_bytes())
        assert response["status"] == "REQUEST_SUCCEEDED"
        for series in response["Results"]["series"]:
            assert series["seriesID"] in SERIES
            for point in series["data"]:
                if point["period"] == "M13":
                    continue
                key = f"{point['year']}-{int(point['period'][1:]):02d}"
                field = SERIES[series["seriesID"]]
                assert field not in by_date.setdefault(key, {})
                by_date[key][field] = float(point["value"])
    assert len(by_date) == 288 and all(set(v) == set(SERIES.values()) for v in by_date.values())
    assert min(by_date) == "2001-01" and max(by_date) == "2024-12"
    return by_date


def summarize(data, low, high):
    pre = [v["openings"] for date, v in data.items() if date < "2020" and low <= v["unemployment"] <= high]
    post = [v["openings"] for date, v in data.items() if "2022" <= date <= "2024-12" and low <= v["unemployment"] <= high]
    assert pre and post
    return {"pre_n": len(pre), "post_n": len(post), "pre_mean": mean(pre),
            "post_mean": mean(post), "difference": mean(post) - mean(pre),
            "pre_median": median(pre), "post_median": median(post)}


def main():
    data = load()
    output = ROOT / "output"
    (ROOT / "research").mkdir(exist_ok=True)
    (output / "figures").mkdir(parents=True, exist_ok=True)
    (output / "tables").mkdir(parents=True, exist_ok=True)
    with (ROOT / "data" / "analysis-panel.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["month", "unemployment_rate_pct", "openings_rate_pct", "window"])
        for date, row in sorted(data.items()):
            period = "baseline" if date < "2020" else "comparison" if date >= "2022" else "excluded_transition"
            writer.writerow([date, row["unemployment"], row["openings"], period])
    primary = summarize(data, 3.5, 4.5)
    check = summarize(data, 4.0, 5.0)
    last_year = [v["openings"] for date, v in data.items() if date.startswith("2024") and 3.5 <= v["unemployment"] <= 4.5]
    assert len(last_year) == 12
    last_year_check = {"n": len(last_year), "mean": mean(last_year), "difference_from_pre": mean(last_year) - primary["pre_mean"]}
    assert primary["pre_n"] + primary["post_n"] <= 264
    source = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(RAW.glob("*.json"))}
    source["scripts/analyze.py"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    results = {"schema_version": "1", "run_id": "bls-beveridge-001", "source_sha256": source,
               "required_bindings": ["primary.pre_n", "primary.post_n", "primary.pre_mean", "primary.post_mean", "primary.difference", "check.difference", "last_year_check.difference_from_pre"],
               "results": {"primary": primary, "check": check, "last_year_check": last_year_check,
                           "sample": {"months_all": len(data), "baseline_months": 228, "comparison_months": 36,
                                      "excluded_transition_months": 24}}}
    (ROOT / "research" / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    row_end = chr(92) * 2
    table = [r"\begin{tabular}{lrrr}", r"\toprule", "Unemployment interval & 2001--19 & 2022--24 & Difference " + row_end, r"\midrule"]
    for label, x in [(r"3.5--4.5\%", primary), (r"4.0--5.0\%", check)]:
        table.append(f"{label} & {x['pre_mean']:.2f} ({x['pre_n']}) & {x['post_mean']:.2f} ({x['post_n']}) & {x['difference']:.2f} " + row_end)
    table += [r"\bottomrule", r"\end{tabular}"]
    (output / "tables" / "means.tex").write_text("\n".join(table) + "\n")
    fig, ax = plt.subplots(figsize=(6, 4))
    for title, predicate, color in [("2001–2019", lambda d: d < "2020", "#27627c"),
                                    ("2022–2024", lambda d: d >= "2022", "#c76035")]:
        points = [row for date, row in sorted(data.items()) if predicate(date)]
        ax.scatter([p["unemployment"] for p in points], [p["openings"] for p in points],
                   label=title, color=color, alpha=.68, s=22)
    ax.set(xlabel="Unemployment rate (%)", ylabel="Job-openings rate (%)", title="U.S. Beveridge-curve observations")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output / "figures" / "beveridge.pdf")
    plt.close(fig)
    print(json.dumps({"primary": primary, "check": check, "last_year_check": last_year_check}, indent=2))


if __name__ == "__main__":
    main()
