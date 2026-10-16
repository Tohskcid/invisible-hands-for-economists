"""Independent two-wave restaurant analysis; no original analysis code used."""
from pathlib import Path
import re, json, hashlib, platform
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from acquire import main as acquire

ROOT = Path(__file__).resolve().parents[1]
SEED = 19920401

def h(path): return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()

def regress(frame, outcome, controls=(), term='state'):
    columns = [term]+list(controls)
    z = frame[[outcome]+columns].dropna()
    y = z[outcome].to_numpy(float)
    x = np.column_stack([np.ones(len(z)),z[columns].to_numpy(float)])
    assert len(z)>x.shape[1] and np.linalg.matrix_rank(x)==x.shape[1]
    inv = np.linalg.inv(x.T@x); b = inv@x.T@y; e=y-x@b
    n,k=x.shape; v0=inv*(e@e)/(n-k)
    v1=inv@(x.T@(x*e[:,None]**2))@inv*n/(n-k)
    return {'estimate':float(b[1]),'std_error':float(np.sqrt(v1[1,1])),
            'se_homoskedastic':float(np.sqrt(v0[1,1])),'n':int(n),
            'n_nj':int(z.state.sum()) if 'state' in z else None,
            'n_pa':int((z.state==0).sum()) if 'state' in z else None,
            'coefficients':dict(zip(['intercept']+columns,b.tolist())),
            'residual_sd':float(np.sqrt(e@e/(n-k))),'outcome':outcome,
            'formula':outcome+' ~ 1 + '+' + '.join(columns),'variance':'HC1; homoskedastic also reported'}

def fte(d,suffix='',pt=.5,managers=True):
    cs=['empft'+suffix,'emppt'+suffix]+(['nmgrs'+suffix] if managers else [])
    return (d['empft'+suffix]+pt*d['emppt'+suffix]+(d['nmgrs'+suffix] if managers else 0)).where(d[cs].notna().all(axis=1))

def main():
    acquire()
    codebook=(ROOT/'data/raw/codebook').read_text(errors='replace')
    cols=[(m.group(1).lower(),int(m.group(2))-1,int(m.group(3))) for l in codebook.splitlines() if (m:=re.match(r'^([A-Z][A-Z0-9_]*)\s+(\d+)\s+(\d+)\s+\d',l))]
    d=pd.read_fwf(ROOT/'data/raw/public.dat',colspecs=[(a,b) for _,a,b in cols],names=[n for n,_,_ in cols],na_values='.')
    assert d.shape==(410,46) and set(d.state.unique())=={0,1}
    d.insert(0,'row_id',np.arange(1,len(d)+1))
    d['fte_pre']=fte(d); d['fte_post']=fte(d,'2')
    # Permanent closures already have all employment components recorded as zero.
    assert (d.loc[d.status2==3,['empft2','emppt2','nmgrs2']]==0).all().all()
    d['change']=d.fte_post-d.fte_pre
    for chain in [2,3,4]: d[f'chain{chain}']=(d.chain==chain).astype(int)
    d['gap']=np.where(d.state==1,np.maximum(5.05-d.wage_st,0)/d.wage_st,0)
    d.loc[(d.state==1)&d.wage_st.isna(),'gap']=np.nan
    d['meal_pre']=d[['psoda','pfry','pentree']].sum(axis=1,min_count=3)
    d['meal_post']=d[['psoda2','pfry2','pentree2']].sum(axis=1,min_count=3)
    d['meal_change']=d.meal_post-d.meal_pre
    d['wage_change']=d.wage_st2-d.wage_st
    d['hours_change']=d.hrsopen2-d.hrsopen
    d['ftshare_pre']=(d.empft+d.nmgrs)/(d.empft+d.nmgrs+d.emppt)
    d['ftshare_post']=(d.empft2+d.nmgrs2)/(d.empft2+d.nmgrs2+d.emppt2)
    d['share_change']=d.ftshare_post-d.ftshare_pre
    d.to_csv(ROOT/'data/processed/restaurants.csv',index=False)
    pair=d.dropna(subset=['change']); controls=['chain2','chain3','chain4','co_owned']
    primary=regress(d,'change')
    a=pair.loc[pair.state==1,'change'].to_numpy(); b=pair.loc[pair.state==0,'change'].to_numpy()
    assert abs(primary['estimate']-(a.mean()-b.mean()))<1e-10
    primary['se_separate_groups']=float(np.sqrt(a.var(ddof=1)/len(a)+b.var(ddof=1)/len(b)))
    rng=np.random.default_rng(SEED)
    draws=np.array([rng.choice(a,len(a),replace=True).mean()-rng.choice(b,len(b),replace=True).mean() for _ in range(2000)])
    primary['bootstrap_low'],primary['bootstrap_high']=map(float,np.quantile(draws,[.025,.975]))
    primary['normal_low']=primary['estimate']-1.96*primary['std_error'];primary['normal_high']=primary['estimate']+1.96*primary['std_error']
    specifications={'primary':primary,'controlled':regress(d,'change',controls),
       'gap':regress(d,'change',[],term='gap'),'gap_controlled':regress(d,'change',controls,term='gap')}
    robust={}
    for pt in [.4,.6]:
        z=d.copy();z['altchange']=fte(z,'2',pt)-fte(z,'',pt);robust[f'pt{str(pt).replace(".","")}']=regress(z,'altchange')
    z=d.copy();z['altchange']=fte(z,'2',managers=False)-fte(z,managers=False);robust['no_managers']=regress(z,'altchange')
    for label,mask in [('no_permanent',d.status2!=3),('phone_only',d.type2==1),('no_shore',d.shore==0)]:robust[label]=regress(d[mask],'change')
    for chain in [1,2,3,4]:robust[f'omit_chain{chain}']=regress(d[d.chain!=chain],'change')
    z=d.copy();low,high=z.change.quantile([.01,.99]);z['trimchange']=z.change.clip(low,high);robust['winsor_changes']=regress(z,'trimchange')
    diagnostic=regress(d[(d.state==0)|((d.state==1)&(d.wage_st>=5.05))],'change')
    outcomes={name:regress(d,col) for name,col in [('starting_wage','wage_change'),('opening_hours','hours_change'),('meal_price','meal_change'),('fulltime_share','share_change')]}
    groups={}
    for state,label in [(0,'pa'),(1,'nj')]:
        z=d[d.state==state];p=z.dropna(subset=['change'])
        groups[label]={'n_raw':len(z),'n_pre':int(z.fte_pre.notna().sum()),'n_post':int(z.fte_post.notna().sum()),'n_pair':len(p),
          'pre':float(z.fte_pre.mean()),'post':float(z.fte_post.mean()),'paired_pre':float(p.fte_pre.mean()),'paired_post':float(p.fte_post.mean()),'change':float(p.change.mean()),
          'missing_pair_rate':float(z.change.isna().mean()),'permanent_closed':int((z.status2==3).sum()),'starting_wage_pre':float(z.wage_st.mean()),'starting_wage_post':float(z.wage_st2.mean())}
    repeated=groups['nj']['post']-groups['nj']['pre']-groups['pa']['post']+groups['pa']['pre']
    result={'primary':primary,'specifications':specifications,'robustness':robust,'outcomes':outcomes,'groups':groups,
      'diagnostic_highwage':diagnostic,'repeated_cross_section':{'estimate':repeated,'note':'Four cell means using available outcomes; not same sample as primary'},
      'audit':{'n_raw':len(d),'n_pairs':len(pair),'duplicate_sheet_rows':d[d.sheet.duplicated(False)].row_id.tolist(),
      'missing_components':d[['empft','emppt','nmgrs','empft2','emppt2','nmgrs2']].isna().sum().to_dict(),'permanent_closed':int((d.status2==3).sum()),'state_clusters':2,'seed':SEED,
      'negative_employment_components':int((d[['empft','emppt','nmgrs','empft2','emppt2','nmgrs2']]<0).sum().sum()),'second_wave_date_range':[int(d.date2.min()),int(d.date2.max())],
      'winsor_limits':[float(low),float(high)],'status_counts':{str(int(k)):int(v) for k,v in d.status2.value_counts().items()}}}
    flat={**specifications,**groups,**{'robust_'+k:v for k,v in robust.items()},**{'outcome_'+k:v for k,v in outcomes.items()},'highwage':diagnostic,'crosssection':result['repeated_cross_section'],'audit':result['audit']}
    out={'schema_version':'1','run_id':'R_BASE','source_sha256':{p:h(p) for p in ['scripts/analyze.py','scripts/acquire.py','data/raw/public.dat','data/raw/codebook','research/data-provenance.json']},
      'required_bindings':['primary.estimate','primary.std_error','primary.n','primary.n_nj','primary.n_pa','primary.se_homoskedastic','primary.bootstrap_low','primary.bootstrap_high'],
      'results':flat}
    (ROOT/'research/results.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    (ROOT/'research/results-detail.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    (ROOT/'research/environment.json').write_text(json.dumps({'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'matplotlib':matplotlib.__version__,'seed':SEED},indent=2))
    def binding(key,value):return rf'\result{{{key}}}{{{value:.2f}}}' if isinstance(value,float) else rf'\result{{{key}}}{{{value}}}'
    def table(name,header,rows):
        text='\\begin{tabular}{'+('l'+'r'*(len(header)-1))+'}\n\\toprule\n'+' & '.join(header)+' \\\\\n\\midrule\n'
        text+=''.join(' & '.join(r)+' \\\\\n' for r in rows)+'\\bottomrule\n\\end{tabular}\n'
        (ROOT/'output/tables'/f'{name}.tex').write_text(text)
    rows=[]
    for label,title in [('pa','Pennsylvania'),('nj','New Jersey')]:
        v=groups[label]; rows.append([title]+[binding(label+'.'+key,v[key]) for key in ['n_raw','n_pair','paired_pre','paired_post','change']])
    table('means',['State','Source rows','Pairs','Pre FTE','Post FTE','Change'],rows)
    rows=[]
    for key,title in [('primary','State contrast'),('controlled','Chain/ownership controls'),('gap','Initial wage gap'),('gap_controlled','Gap with controls')]:
        v=specifications[key];prefix=key
        rows.append([title]+[binding(prefix+'.'+k,v[k]) for k in ['estimate','std_error','se_homoskedastic','n']])
    table('main',['Specification','Estimate','HC1 SE','OLS SE','N'],rows)
    labels={'pt04':'Part-time weight 0.4','pt06':'Part-time weight 0.6','no_managers':'Exclude managers','no_permanent':'Omit permanent closures','phone_only':'Phone interviews','no_shore':'Omit shore locations','winsor_changes':'Winsorized changes','omit_chain1':'Omit Burger King','omit_chain2':'Omit KFC','omit_chain3':'Omit Roy Rogers','omit_chain4':"Omit Wendy's"}
    table('robustness',['Variant','Estimate','HC1 SE','N'],[[labels[k]]+[binding('robust_'+k+'.'+a,v[a]) for a in ['estimate','std_error','n']] for k,v in robust.items()])
    labels={'starting_wage':'Starting wage (dollars/hour)','opening_hours':'Opening hours/day','meal_price':'Meal price (dollars)','fulltime_share':'Full-time share (fraction)'}
    table('outcomes',['Outcome change','NJ--PA','HC1 SE','N'],[[labels[k]]+[binding('outcome_'+k+'.'+a,v[a]) for a in ['estimate','std_error','n']] for k,v in outcomes.items()])
    fig,ax=plt.subplots(figsize=(6,3.6))
    for label,title,color in [('nj','New Jersey','#1b4d6b'),('pa','Pennsylvania','#6b4d1b')]:
        g=groups[label];ax.plot([0,1],[g['paired_pre'],g['paired_post']],marker='o',label=title,color=color)
    ax.set(xticks=[0,1],xticklabels=['Before','After'],ylabel='Mean FTE employment (complete pairs)');ax.legend(frameon=False);ax.spines[['top','right']].set_visible(False);fig.tight_layout();fig.savefig(ROOT/'output/figures/employment.pdf');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(7,3.2),sharex=True,sharey=True)
    bins=np.arange(3.9,6.31,.15)
    for ax,col,title in zip(axes,['wage_st','wage_st2'],['Before','After']):
        for state,label,color in [(1,'NJ','#1b4d6b'),(0,'PA','#6b4d1b')]:ax.hist(d.loc[d.state==state,col].dropna(),bins=bins,density=True,histtype='step',linewidth=1.5,label=label,color=color)
        ax.axvline(5.05,color='black',linestyle=':',linewidth=1);ax.set(title=title,xlabel='Starting wage (dollars/hour)');ax.spines[['top','right']].set_visible(False)
    axes[0].set_ylabel('Density');axes[1].legend(frameon=False);fig.tight_layout();fig.savefig(ROOT/'output/figures/wages.pdf');plt.close(fig)
    print(json.dumps({'primary':primary,'groups':groups,'results':'research/results.json'},indent=2))

if __name__=='__main__':main()
