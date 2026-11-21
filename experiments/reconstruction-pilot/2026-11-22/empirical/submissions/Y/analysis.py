"""Run in the task directory with Python 3 and NumPy."""
from pathlib import Path
from collections import Counter
import json
import re
import numpy as np

book = Path("input/codebook").read_text(encoding="latin1")
fields = re.findall(r"^([A-Z][A-Z0-9_]*) +([0-9]+) +([0-9]+) +\d+\.\d+", book, re.M)
lines = Path("input/observations.dat").read_text().splitlines()
def column(start, end):
    cells = [line[int(start)-1:int(end)].strip() for line in lines]
    return np.array([np.nan if s in ("", ".") else float(s) for s in cells])

d = {k: column(a, b) for k, a, b in fields}
nj, status = d["STATE"], d["STATUS2"]
assert len(lines) == 410 and len(fields) == 46 and set(nj) == {0, 1}
states = ["PA", "NJ"]
base = np.ones(len(nj), dtype=bool)
permanent = status == 3
active = status == 1
def did(a, b, keep=base):
    groups = {}
    for i, state in enumerate(states):
        m = (nj == i) & keep & np.isfinite(a+b)
        delta = b[m]-a[m]
        groups[state] = dict(n=int(m.sum()), pre=a[m].mean(), post=b[m].mean(),
                             change=delta.mean(), var_mean=delta.var(ddof=1)/len(delta))
    effect = groups["NJ"]["change"]-groups["PA"]["change"]
    se = np.sqrt(sum(g["var_mean"] for g in groups.values()))
    return dict(**groups, did=effect, se=se, ci95=[effect-1.96*se, effect+1.96*se])

def employment(suffix, weight):
    return d["EMPFT"+suffix]+d["NMGRS"+suffix]+weight*d["EMPPT"+suffix]

def closed_zero(x, all_closed=False):
    return np.where(permanent | (all_closed & (status>=2)), 0, np.where(active, x, np.nan))

a, b = [employment(s, .5) for s in ("", "2")]
post = closed_zero(b)
main = did(a, post)
sens = {"operating": did(a,b,active), "all_closures_zero": did(a,closed_zero(b,True))}
for w in (.25,.75,1):
    sens[f"PT_weight_{w}"] = did(employment("",w),closed_zero(employment("2",w)))
for k in ("EMPFT","NMGRS","EMPPT"):
    sens[k] = did(d[k],closed_zero(d[k+"2"]),np.isfinite(a+post))
ops = {}
for k in ("WAGE_ST","HRSOPEN","NREGS","NREGS11","FIRSTINC","INCTIME"):
    ops[k]=did(d[k],d["FIRSTIN2" if k=="FIRSTINC" else k+"2"],active)
def meals(allowed, suffix):
    x=d["MEALS"+suffix]
    return np.where(np.isfinite(x),100*np.isin(x,allowed),np.nan)
for label, codes in [("any_meal",[1,2,3]),("free_meal",[1,3])]:
    ops[label]=did(meals(codes,""),meals(codes,"2"),active)
def basket(s):
    return sum(d[k+s] for k in ("PSODA","PFRY","PENTREE"))
ops["basket"]=did(basket(""),basket("2"),active)
ops["log_basket_x100"]=did(100*np.log(basket("")),100*np.log(basket("2")),active)

# Each coefficient uses its own complete cases and HC1 covariance.
controls=[d["CHAIN"]==i for i in (2,3,4)]+[d["CO_OWNED"]]
def adjusted(y, exposure, keep):
    X=np.column_stack([np.ones(len(nj)),exposure,*controls])
    m=keep & np.isfinite(y) & np.isfinite(X).all(axis=1)
    X, y=X[m],y[m]
    beta,_,rank,_=np.linalg.lstsq(X,y,rcond=None)
    n,k=X.shape
    assert rank==k
    bread=np.linalg.inv(X.T@X)
    scores=X*(y-X@beta)[:,None]
    se=np.sqrt((bread@(scores.T@scores)@bread)[1,1]*n/(n-k))
    return dict(n=n,coefficient=beta[1],se=se,ci95=[beta[1]-1.96*se,beta[1]+1.96*se])

gap=np.maximum(0,5.05-d["WAGE_ST"])
reg={"employment":adjusted(post-a,nj,base),
     "log_basket_x100":adjusted(100*np.log(basket("2")/basket("")),nj,active),
     "NJ_gap_employment":adjusted(post-a,gap,nj==1),
     "NJ_gap_wage":adjusted(d["WAGE_ST2"]-d["WAGE_ST"],gap,(nj==1)&active)}
reg["NJ_gap_log_basket_x100"] = adjusted(100*np.log(basket("2")/basket("")),gap,(nj==1)&active)
audit={}
for i,state in enumerate(states):
    m=nj==i
    audit[state]=dict(n=int(m.sum()), followup={int(k):v for k,v in Counter(status[m]).items()},
                      wage_below_new_floor_pre=float(np.mean(d["WAGE_ST"][m & np.isfinite(d["WAGE_ST"])]<5.05)),
                      missing_baseline_FTE=int(sum(m & ~np.isfinite(a))),
                      missing_followup_FTE=int(sum(m & ~np.isfinite(post))))
    audit[state]["wage_distribution"] = {}
    for suffix in ("","2"):
        x = d["WAGE_ST"+suffix][m]
        audit[state]["wage_distribution"]["post" if suffix else "pre"] = {
            "observed": int(np.isfinite(x).sum()), "at_5.05": int(sum(x==5.05)),
            "below_5.05": int(sum(x<5.05))}
    audit[state]["permanent_closure_rate"] = float(permanent[m].mean())
# Lines already pair the two reports, including the two rows labeled 407.
complete = np.isfinite(a+post)
leave_one = [did(a,post,np.arange(len(nj))!=i)["did"] for i in np.flatnonzero(complete)]
odd_date = np.isfinite(d["DATE2"]) & (d["DATE2"]%100 != 92)
quality = dict(repeated_sheet_numbers=[int(k) for k,v in Counter(d["SHEET"]).items() if v>1],
               unexpected_year_codes=d["DATE2"][odd_date].tolist(),
               did_excluding_unexpected_year=did(a,post,~odd_date)["did"],
               leave_one_out_range=[min(leave_one),max(leave_one)])
assert np.isclose(main["did"],sens["EMPFT"]["did"]+sens["NMGRS"]["did"]+.5*sens["EMPPT"]["did"])
res=dict(quality=quality,audit=audit,employment=main,sensitivity=sens,operations=ops,adjusted=reg)
Path("results.json").write_text(json.dumps(res,indent=2,allow_nan=False)+"\n")
