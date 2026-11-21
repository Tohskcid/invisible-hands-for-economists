"""Run python3 analysis.py in the task directory. Standard library only."""
from collections import Counter
from datetime import datetime
from pathlib import Path
import json
import math
import re
from statistics import mean, variance

book = Path("input/codebook").read_text(encoding="latin1")
fields = [(k, int(a)-1, int(b)) for k, a, b in
          re.findall(r"^([A-Z][A-Z0-9_]*)\s+(\d+)\s+(\d+)\s+\d+\.\d+", book, re.M)]
rows = []
for line in Path("input/observations.dat").read_text().splitlines():
    vals = [line[a:b].strip() for _, a, b in fields]
    assert vals == line.split()
    rows.append({k: None if v == "." else float(v)
                 for (k, _, _), v in zip(fields, vals)})
assert len(fields) == 46 and len(rows) == len({(r['STATE'], r['SHEET']) for r in rows}) == 410
states = ['PA', 'NJ']

def value(r, metric, post, closure):
    status = r['STATUS2']
    jobs = metric in ('fte','head','ft','pt','mgr','nonmgr')
    if post and status != 1:
        if jobs and ((status == 3 and closure != 'open') or
                     (status in (2,4,5) and closure == 'all')):
            return 0.
        return None
    suffix = '2' if post else ''
    components = {'fte': [('EMPFT',1),('EMPPT',.5),('NMGRS',1)],
                  'head': [('EMPFT',1),('EMPPT',1),('NMGRS',1)],
                  'nonmgr': [('EMPFT',1),('EMPPT',.5)],
                  'ft':[('EMPFT',1)], 'pt':[('EMPPT',1)], 'mgr':[('NMGRS',1)],
                  'meal':[('PSODA',1),('PFRY',1),('PENTREE',1)]}
    if metric in ('free', 'discount'):
        v = r['MEALS'+suffix]
        return None if v is None else 100.*(v in ((1,3) if metric=='free' else (2,3)))
    if metric == 'FIRSTINC' and post:
        return r['FIRSTIN2']
    terms = components.get(metric, [(metric,1)])
    if any(r[k+suffix] is None for k,_ in terms):
        return None
    return sum(r[k+suffix]*w for k,w in terms)

def summarize(pairs):
    delta = [b-a for a,b in pairs]
    return dict(n=len(delta), before=mean(a for a,b in pairs),
                after=mean(b for a,b in pairs), change=mean(delta),
                variance=variance(delta))

def compare(metric, subset=rows, closure='permanent'):
    out = {}
    for s,name in enumerate(states):
        pairs=[(value(r,metric,False,closure), value(r,metric,True,closure))
               for r in subset if r['STATE']==s]
        out[name]=summarize([p for p in pairs if None not in p])
    d = out['NJ']['change'] - out['PA']['change']
    se = math.sqrt(sum(out[n]['variance']/out[n]['n'] for n in states))
    out.update(did=d, conditional_se=se, conditional_interval=[d-1.96*se,d+1.96*se])
    return out

res = {'audit':{}, 'estimates':{}, 'sensitivity':{}, 'wage_groups_NJ':{}}
for s,name in enumerate(states):
    rr = [r for r in rows if r['STATE']==s]
    dates = [datetime.strptime(str(int(r['DATE2'])).zfill(6),'%m%d%y').date().isoformat()
             for r in rr if r['DATE2'] is not None]
    res['audit'][name] = dict(n=len(rr), statuses=Counter(int(r['STATUS2']) for r in rr),
        chains=Counter(int(r['CHAIN']) for r in rr),dates=[min(dates),max(dates)],
        fte_available=[sum(value(r,'fte',p,'permanent') is not None for r in rr) for p in (0,1)])
res['repeated_sheet_numbers']=[int(k) for k,n in Counter(r['SHEET'] for r in rows).items() if n>1]
for metric in ('fte','head','nonmgr','ft','pt','mgr','WAGE_ST','meal','HRSOPEN','free','discount',
               'NREGS','NREGS11','FIRSTINC','INCTIME'):
    res['estimates'][metric]=compare(metric)
for rule in ('open','all'):
    res['sensitivity'][rule]=compare('fte',closure=rule)
for area in ('PA1','PA2'):
    res['sensitivity'][area]=compare('fte',[r for r in rows if r['STATE']==1 or r[area]==1])
for metric in ('fte','meal'):
    by_chain = [compare(metric,[r for r in rows if r['CHAIN']==k]) for k in range(1,5)]
    res['sensitivity'][metric+'_by_chain']=by_chain
    res['sensitivity'][metric+'_NJ_chain_weighted']=sum(b['NJ']['n']*b['did'] for b in by_chain)/sum(b['NJ']['n'] for b in by_chain)
for label, predicate in [('at_old_floor',lambda w:w==4.25),('between',lambda w:4.25<w<5.05),
                         ('at_or_above_new_floor',lambda w:w>=5.05)]:
    rr=[r for r in rows if r['STATE']==1 and r['WAGE_ST'] is not None and predicate(r['WAGE_ST'])]
    group={'baseline_n':len(rr)}
    for m in ('WAGE_ST','fte','meal'):
        pairs=[tuple(value(r,m,p,'permanent') for p in (False, True)) for r in rr]
        group[m]=summarize([p for p in pairs if None not in p])
    res['wage_groups_NJ'][label]=group
assert sum(b['NJ']['n'] for b in res['sensitivity']['fte_by_chain']) == res['estimates']['fte']['NJ']['n']
def in_window(r):
    if r['DATE2'] is None:
        return False
    date = datetime.strptime(str(int(r['DATE2'])).zfill(6), '%m%d%y')
    return datetime(1992,11,5) <= date <= datetime(1992,12,31)

res['outside_window_or_missing'] = [
    [int(r['STATE']), int(r['SHEET']), r['DATE2']] for r in rows if not in_window(r)]
res['sensitivity']['dated_in_window'] = compare('fte', [r for r in rows if in_window(r)])
res['sensitivity']['nonshore'] = compare('fte',[r for r in rows if r['SHORE']==0])
main_sample = [r for r in rows if all(value(r,'fte',post,'permanent') is not None for post in (0,1))]
res['matched_components'] = {m:compare(m,main_sample) for m in ('ft','pt','mgr')}
parts=res['matched_components']
assert math.isclose(parts['ft']['did'] + .5*parts['pt']['did'] + parts['mgr']['did'],
                    res['estimates']['fte']['did'])
Path('results.json').write_text(json.dumps(res,indent=2,allow_nan=False)+'\n')
