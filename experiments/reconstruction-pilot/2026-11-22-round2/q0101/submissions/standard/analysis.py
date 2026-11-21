"""Run with Python 3 and NumPy in the supplied directory."""
import csv
import json
import math
from pathlib import Path

import numpy as np

root = Path(__file__).resolve().parent
with (root / 'inputs/input-1.csv').open() as stream:
    rows = list(csv.DictReader(stream))
fields = list(rows[0])
samples = ['N', 'I', 'O']
results = {}

def fit(y, columns):
    x = np.column_stack([np.ones(len(y)), *columns])
    b = np.linalg.lstsq(x, y, rcond=None)[0]
    resid = y - x @ b
    df = len(y) - len(b)
    rss = resid @ resid
    cov = np.linalg.inv(x.T @ x) * rss / df
    return dict(b=b, se=np.sqrt(cov.diagonal()), cov=cov, df=df, rss=rss,
                rmse=np.sqrt(rss / df), adj=1-rss/df/np.var(y, ddof=1))

def f_tail(f, q, df):
    # Integrate the F survival probability after the beta substitution
    # x = df/(df+qF), then t=x*u**(1/a) to cancel t**(a-1).
    a, b = df/2, q/2
    x = df/(df+q*f)
    # further substitute u=exp(-v); Gauss-Legendre on v in [0,60]
    nodes, weights = np.polynomial.legendre.leggauss(240)
    v = 30*(1+nodes)
    scale = math.exp(a*math.log(x)-math.log(a)+math.lgamma(a+b)-math.lgamma(a)-math.lgamma(b))
    return min(1., scale*30*(weights @ (np.exp(-v)*(1-x*np.exp(-v/a))**(b-1))))

def wald(m, gradient, value):
    f = value**2 / (gradient @ m['cov'] @ gradient)
    return [f, f_tail(f, 1, m['df'])]

def derived(m, fn):
    b = m['b']
    grad = np.column_stack([(fn(b+d)-fn(b-d))/2e-6 for d in 1e-6*np.eye(len(b))])
    return [fn(b), np.sqrt(np.diag(grad @ m['cov'] @ grad.T))]

for sample, flag in zip(samples, fields[1:4]):
    data = np.array([[float(r[k]) for k in fields[4:]] for r in rows if r[flag]=='1'])
    initial, final, aggregate, pop, invest, enroll = data.T
    x, y = np.log(initial), np.log(final)
    change = y-x
    q = .05+pop/100
    k, h, z = np.log(invest/100), np.log(enroll/100), np.log(q)
    s = results[sample] = dict(n=len(x), qmean=q.mean())
    for model in ['L1','L2','G0','G1','G2']:
        growth = model[0]=='G'
        count = int(model[1])
        dep = change if growth else y
        base = [x] if growth else []
        stocks = [k,h][:count]
        m = s[model] = fit(dep, base+stocks+([z] if count else []))
        if growth:
            m['speed'] = derived(m, lambda b: np.array([-100*np.log1p(b[1])/25]))
        if not count:
            continue
        gvec = np.ones(len(m['b']))
        gvec[:1+int(growth)] = 0
        m['test'] = wald(m, gvec, gvec @ m['b'])
        r = s[model+'R'] = fit(dep, base+[v-z for v in stocks])
        def params(b):
            slopes = b[1+int(growth):]
            scale = -b[1] if growth else 1
            shares = slopes/(scale+sum(slopes))
            return np.r_[-100*np.log1p(b[1])/25,shares] if growth else shares
        r['parameters'] = derived(r, params)
        if growth:
            # Derivative of the common-speed consistency gap at mean q
            def gap(b):
                speed, *shares = params(b)
                return np.array([speed-100*q.mean()*(1-sum(shares))])
            r['mean_q_gap'] = derived(r,gap)
            # Test the benchmark country-specific transition against additive
            # departures in the initial-income and normalized input slopes.
            d = 1-count/3
            weight = -np.expm1(-25*q*d)
            target = change-.5-weight*(sum(v-z for v in stocks)/(3*d)-x)
            design = weight[:,None]
            intercept = np.linalg.lstsq(design,target,rcond=None)[0]
            err = target-design@intercept
            free = np.column_stack([design,x,*[v-z for v in stocks]])
            err2 = target-free@np.linalg.lstsq(free,target,rcond=None)[0]
            df = len(x)-free.shape[1]
            f = ((err@err)/(err2@err2)-1)*df/(1+count)
            r['benchmark'] = [f,f_tail(f,1+count,df)]
    s['school_projection'] = fit(h,[k,z])
    returns = q/(3*invest/100)-.03
    s['returns_pct'] = [100*returns.mean(),100*returns.std(ddof=1)]
    def partial(v):
        design = np.column_stack([np.ones(len(x)),k,h,z])
        return v-design@np.linalg.lstsq(design,v,rcond=None)[0]
    s['plot'] = [np.column_stack([x,change]),np.column_stack([partial(x),partial(change)])]

def encode(v):
    return v.tolist() if hasattr(v,'tolist') else int(v)
(root/'results.json').write_text(json.dumps(results,default=encode,indent=2)+'\n')
if __name__=='__main__':
    for model in ['L1','L1R','L2','L2R','G0','G1','G1R','G2','G2R']:
        for sample in samples:
            a = results[sample][model]
            def fmt(x): return '/'.join(f'{v:.3f}' for v in x)
            print(model,sample,fmt(a['b']),fmt(a['se']),fmt([a['adj'],a['rmse']]),
                  *[fmt(np.ravel(a[key])) for key in ['test','speed','parameters','benchmark','mean_q_gap'] if key in a])
    for sample in samples:
        s=results[sample]
        print(sample,s['n'],s['qmean'],s['school_projection']['b'],s['school_projection']['se'],s['returns_pct'])
