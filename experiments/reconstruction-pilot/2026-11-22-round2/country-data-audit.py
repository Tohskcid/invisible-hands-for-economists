"""Recompute Table I and the printed page 420 correlations from the released country CSV."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import correlation

import numpy as np


def audit(path):
    with path.open(newline='', encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    fits = {}
    for sample in ('sample_nonoil', 'sample_intermediate', 'sample_oecd'):
        group = [r for r in rows if r[sample] == '1']
        response = [math.log(float(r['output_per_working_age_1985'])) for r in group]
        design = [[1., math.log(float(r['investment_pct']) / 100),
                   math.log(float(r['working_age_growth_pct']) / 100 + .05)] for r in group]
        slopes = np.linalg.lstsq(design, response, rcond=None)[0]
        fits[sample] = {'n': len(group), 'coefficients': slopes.tolist()}
    group = [r for r in rows if r['sample_intermediate'] == '1']
    school = [float(r['schooling_pct']) for r in group]
    correlations = {}
    for key in ('investment_pct', 'working_age_growth_pct'):
        values = [float(r[key]) for r in group]
        value = correlation(school, values)
        if not math.isclose(value, np.corrcoef(school, values)[0, 1], abs_tol=1e-12):
            raise ValueError('correlation implementations disagree')
        correlations[key] = value
    return {'input_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'article': '10.2307/2118477', 'table_I_columns': ['intercept', 'log investment share', 'log(n + 0.05)'],
            'table_I_recomputed': fits, 'page_420_intermediate_n': len(group),
            'page_420_pearson_correlation_with_schooling': correlations,
            'page_420_printed': {'investment_pct': 0.59, 'working_age_growth_pct': -0.38}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    print(json.dumps(audit(parser.parse_args().csv), indent=2, allow_nan=False))
