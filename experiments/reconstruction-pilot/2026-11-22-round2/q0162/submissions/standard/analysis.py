"""Run with Python 3 and NumPy from any directory; write results beside this file."""
import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
GROUPS = dict(Broad="sample_nonoil", Intermediate="sample_intermediate", OECD="sample_oecd")
FIELDS = ["output_per_working_age_1960", "output_per_working_age_1985",
          "investment_pct", "working_age_growth_pct", "schooling_pct"]


def fit(y, columns):
    X = np.column_stack([np.ones(len(y)), *columns.values()])
    b, _, rank, _ = np.linalg.lstsq(X, y, rcond=None)
    assert rank == X.shape[1]
    u = y - X @ b
    inv = np.linalg.inv(X.T @ X)
    h = ((X @ inv) * X).sum(axis=1)
    scores = X * (u / (1 - h))[:, None]
    cov = inv @ scores.T @ scores @ inv
    names = ["constant", *columns]
    r2 = 1 - u @ u / ((y-y.mean()) @ (y-y.mean()))
    return dict(coef=dict(zip(names, b)), hc3_se=dict(zip(names, np.sqrt(cov.diagonal()))),
                hc3_cov=cov.tolist(), r2=r2, adj_r2=1-(1-r2)*(len(y)-1)/(len(y)-rank))


def analyze(rows):
    y0, y1, inv, n, school = np.array([[float(row[k]) for k in FIELDS] for row in rows]).T
    init, end, s, d, h = map(np.log, [y0, y1, inv/100, .05+n/100, school/100])
    result = dict(N=len(rows), mean_annual_log_growth_pct=4*(end-init).mean(),
                  sd_log_output=[float(x.std(ddof=1)) for x in (init,end)], models={})
    for growth in [False, True]:
        y = end-init if growth else end
        prefix = "growth" if growth else "level"
        base = dict(initial=init) if growth else {}
        if growth:
            result["models"]["absolute"] = fit(y, base)
        for aug in [False, True]:
            name = prefix + ("_aug" if aug else "_basic")
            free = fit(y, dict(**base, investment=s, dilution=d, **({"school":h} if aug else {})))
            weights = np.array([float(k in ("investment","dilution","school")) for k in free["coef"]])
            free["restriction_z"] = sum(v*w for v,w in zip(free["coef"].values(),weights)) / np.sqrt(weights @ free["hc3_cov"] @ weights)
            constrained = fit(y, dict(**base, physical=s-d, **({"human":h-d} if aug else {})))
            b = constrained["coef"]
            q = -b["initial"] if growth else 1.
            denom = q + b["physical"] + b.get("human",0.)
            constrained.update(alpha=b["physical"]/denom, beta=b.get("human",0.)/denom)
            result["models"][name] = free
            result["models"][name+"_restricted"] = constrained
    for model in result["models"].values():
        if "initial" in model["coef"]:
            rho = 1+model["coef"]["initial"]
            model["annual_speed_pct"] = -4*np.log(rho)
            model["speed_se_pct"] = 4*model["hc3_se"]["initial"]/rho
    return result


def main():
    with (ROOT/"inputs/input-1.csv").open() as f:
        rows = list(csv.DictReader(f))
    assert len({row["country"] for row in rows}) == len(rows)
    membership = {}
    for row in rows:
        flags = "".join(row[k] for k in GROUPS.values())
        membership[flags] = membership.get(flags, 0)+1
    results = dict(total=len(rows), membership=membership, groups={})
    for label,key in GROUPS.items():
        selected = [row for row in rows if row[key]=="1"]
        assert all(row[k] != "" for row in selected for k in FIELDS)
        results["groups"][label] = analyze(selected)
    (ROOT/"results.json").write_text(json.dumps(results, indent=2, allow_nan=False)+"\n")


if __name__ == "__main__":
    main()
