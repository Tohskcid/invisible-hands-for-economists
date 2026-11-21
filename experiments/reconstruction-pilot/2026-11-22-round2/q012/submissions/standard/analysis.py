"""Reproduce results.json with Python 3 (standard library only)."""
import csv
import json
import math
from pathlib import Path
from statistics import NormalDist

ROOT = Path(__file__).resolve().parent
ALPHA = 0.1
LEVELS = (0.05, 0.10, 0.20)
H = 0.006
NORMAL = NormalDist()


def tail(z):
    return 0.5 * math.erfc(z / math.sqrt(2))


def posterior_scores(y, s):
    # Gaussian deconvolution kernel, followed by the normal updating formula.
    widths = [math.sqrt(H**2 - se**2) for se in s]
    lo, hi = min(y) - 12 * H, max(y) + 12 * H
    for _ in range(80):
        x = (lo + hi) / 2
        upper_mass = sum(tail((x - mu) / b) for mu, b in zip(y, widths)) / len(y)
        if upper_mass > ALPHA:
            lo = x
        else:
            hi = x
    cutoff = (lo + hi) / 2
    scores = []
    for obs, se in zip(y, s):
        weights, contributions = [], []
        for mu, b in zip(y, widths):
            v = b*b + se*se
            w = math.exp(-0.5 * (obs - mu)**2 / v) / math.sqrt(v)
            mean = (mu * se**2 + obs * b*b) / v
            sd = b * se / math.sqrt(v)
            weights.append(w)
            contributions.append(w * tail((cutoff - mean) / sd))
        scores.append(sum(contributions) / sum(weights))
    return cutoff, scores


def ordered_tests(y, s):
    return sorted((tail((a - b) / math.hypot(s[i], s[j])), i, j)
                  for i, a in enumerate(y) for j, b in enumerate(y) if i != j)


def evaluate(rows):
    y = [float(r['mobility_estimate']) for r in rows]
    s = [float(r['mobility_standard_error']) for r in rows]
    n = len(rows)
    assert n == 100 and len({r['zone_id'] for r in rows}) == n
    assert all(0 < se < H for se in s)
    q, scores = posterior_scores(y, s)
    tests = ordered_tests(y, s)
    order = sorted(range(n), key=lambda i: -scores[i])
    records = [dict(zone_id=int(r['zone_id']), name=r['zone_name'], estimate=y[i],
                    se=s[i], probability=scores[i], levels={}) for i, r in enumerate(rows)]
    summaries = {}
    for gamma in LEVELS:
        selected = set()
        false_sum = 0.
        for k, i in enumerate(order, 1):
            proposed = false_sum + 1 - scores[i]
            if proposed > k * gamma:
                break
            selected.add(i)
            false_sum = proposed
        lower = [1] * n
        upper = [n] * n
        for t, (pv, i, j) in enumerate(tests):
            if pv > gamma / (len(tests) - t):
                break
            lower[i] += 1
            upper[j] -= 1
        ranked = [i for i in range(n) if lower[i] > 90]
        for i, rec in enumerate(records):
            rec['levels'][str(gamma)] = dict(distribution=i in selected,
                                              fixed=i in ranked, lower=lower[i], upper=upper[i])
        summaries[str(gamma)] = dict(distribution=[rows[i]['zone_name'] for i in sorted(selected)],
                                     fixed=[rows[i]['zone_name'] for i in ranked],
                                     mean_posterior_error=false_sum/max(1,len(selected)))
    return dict(bandwidth=H, alpha=ALPHA, cutoff=q, summaries=summaries, areas=records)


if __name__ == '__main__':
    with (ROOT / 'inputs/input-001.csv').open() as f:
        rows = sorted(csv.DictReader(f), key=lambda r: (-float(r['mobility_estimate']), int(r['zone_id'])))
    result = evaluate(rows)
    (ROOT / 'results.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(result['cutoff'], json.dumps(result['summaries'], indent=2))
