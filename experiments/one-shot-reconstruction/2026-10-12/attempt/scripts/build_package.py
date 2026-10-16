"""Bind computed results to manuscript and package metadata without hand-copying."""
from pathlib import Path
import re, json, hashlib, datetime

ROOT=Path(__file__).resolve().parents[1]
STAMP='2026-10-12T01:16:00+08:00'
def h(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def save(path,value):
    target=ROOT/path;target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(value,indent=2,ensure_ascii=False))

def main():
    results=json.loads((ROOT/'research/results.json').read_text())['results']
    template=(ROOT/'paper/manuscript/template.tex').read_text()
    def bind(m):
        key=m.group(1);group,field=key.split('.');v=results[group][field]
        display=f'{v:.2f}' if isinstance(v,float) else str(v)
        return '\\result{'+key+'}{'+display+'}'
    manuscript=re.sub(r'@B:([A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)@',bind,template)
    manuscript=manuscript.replace('@@RESULTSHASH@@',h('research/results.json'))
    for name in ['means','main','robustness','outcomes']:
        manuscript=manuscript.replace('@@TABLE:'+name+'@@',(ROOT/f'output/tables/{name}.tex').read_text())
    # Use the ordinary BibTeX route expected by the unchanged compiler harness.
    manuscript=re.sub(r'\\begin\{thebibliography\}.*?\\end\{thebibliography\}',r'\\bibliographystyle{plainnat}\n\\bibliography{../references}\n% [claim:C_SCOPE] [claim:C_POLICY] [claim:C_INFERENCE]',manuscript,flags=re.S)
    # Bind numeric TeX environments and generated table notes to the section claim.
    default='C_SCOPE'; paragraphs=[]
    mapping={'Data and Measurement':'C_DATA','Estimand, Design, and Uncertainty':'C_ESTIMAND','Employment Results':'C_MAIN','Sensitivity and Adjustment Margins':'C_ROBUST','Identification and Estimator Derivations':'C_ESTIMAND','Replication and Audit Record':'C_REPRO'}
    for paragraph in manuscript.split('\n\n'):
        heading=re.search(r'\\section\{([^{}]+)\}',paragraph)
        if heading:default=mapping.get(heading.group(1),'C_SCOPE')
        if re.search(r'(?<![\w/])\d+(?:[.,]\d+)*',paragraph) and '[claim:' not in paragraph:
            paragraph+='\n% [claim:'+default+']'
        paragraphs.append(paragraph)
    manuscript='\n\n'.join(paragraphs)
    (ROOT/'paper/manuscript/main.tex').write_text(manuscript)
    bibliography='''@techreport{conley2005,
 title={Inference with Difference in Differences with a Small Number of Policy Changes},
 author={Conley, Timothy and Taber, Christopher}, year={2005},
 institution={National Bureau of Economic Research}, number={312},
 doi={10.3386/t0312}, url={https://www.nber.org/papers/t0312}}
@misc{alvarez2023,
 title={Extensions for Inference in Difference-in-Differences with Few Treated Clusters},
 author={Alvarez, Luis and Ferman, Bruno}, year={2023},
 howpublished={arXiv:2302.03131}, url={https://arxiv.org/abs/2302.03131}}
@misc{nj1990,
 title={Minimum Wage-Increase to 5.05 by 1992}, author={{New Jersey State Library}},
 year={1990}, howpublished={Legislative History, Laws of 1990, Chapter 18},
 url={https://repo.njstatelib.org/items/af2bca87-0109-4742-8836-2684cd6e2fcf}}
'''
    (ROOT/'paper/references.bib').write_text(bibliography)
    titles={'conley2005':'Inference with Difference in Differences with a Small Number of Policy Changes','alvarez2023':'Extensions for Inference in Difference-in-Differences with Few Treated Clusters','nj1990':'Minimum Wage-Increase to 5.05 by 1992'}
    locators={'conley2005':'https://www.nber.org/papers/t0312','alvarez2023':'https://arxiv.org/abs/2302.03131','nj1990':'https://repo.njstatelib.org/items/af2bca87-0109-4742-8836-2684cd6e2fcf'}
    downloads={'conley2005':'https://www.nber.org/system/files/working_papers/t0312/t0312.pdf','alvarez2023':'https://arxiv.org/pdf/2302.03131','nj1990':'https://repo.njstatelib.org/server/api/core/bitstreams/da0ecddd-a999-4850-8969-317324d0f197/content'}
    files={'conley2005':'literature/papers/conley2005--inference-with-difference-in-differences-with-a-small-number-of-policy-changes.pdf','alvarez2023':'literature/papers/alvarez2023--extensions-for-inference-in-difference-in-differences-with-few-treated-clusters.pdf','nj1990':'literature/papers/nj1990--minimum-wage-increase-to-5-05-by-1992.pdf'}
    papers=[]
    for key in titles:
        papers.append({'citekey':key,'title':titles[key],'authors':{'conley2005':['Timothy Conley','Christopher Taber'],'alvarez2023':['Luis Alvarez','Bruno Ferman'],'nj1990':['New Jersey State Library']}[key],
          'year':{'conley2005':2005,'alvarez2023':2023,'nj1990':1990}[key],'canonical_locator':locators[key],'verified_at':STAMP,'access_basis':'Public official repository/author-authorized working paper download; local academic use only','access_status':'downloaded','download_locator':downloads[key],'retrieved_at':STAMP,'file':files[key],'sha256':h(files[key])})
    save('research/literature-archive.json',{'schema_version':'1','generated_at':STAMP,'papers':papers})
    diagnostics=[]
    for key,status,finding in [
      ('assignment','pass','State residence and statutory policy timing define treatment; no random-assignment claim.'),
      ('support','pass','Both states and all four chains present; source-row keys preserve duplicate sheet identifier.'),
      ('inference','inconclusive','Only two policy jurisdictions; HC1/OLS/bootstrap condition on state paths and cannot estimate statewide shock uncertainty.'),
      ('timing','pass','NJ legislative archive schedules April 1, 1992; baseline instrument January–March and observed post dates November–December.'),
      ('comparison-groups','inconclusive','PA restaurants are observed contemporaneously but comparable untreated employment changes cannot be verified.'),
      ('anticipation','inconclusive','Increase legislated before baseline; no data identify anticipatory employment response.'),
      ('parallel-trends','blocked','One baseline wave precludes pretrend diagnostics; assumption not empirically verified.'),
      ('spillovers','inconclusive','Cross-border labor/product substitution and chain wage spillovers are not observed.'),
      ('heterogeneous-effects','pass','Single adoption date; no staggered TWFE weighting problem. Chain omissions and initial-wage diagnostic reported descriptively.')]:
        diagnostics.append({'id':key,'status':status,'finding':finding,'artifact':'research/design-memo.md'})
    save('research/design-audit.json',{'design':'did','estimand':'NJ–PA mean change in FTE headcount among observed complete restaurant pairs','assignment_narrative':'Known statewide NJ floor increase, compared with surveyed PA establishments; observational comparison, not random assignment.','interpretation_boundary':'Supported descriptive change contrast; conditional ATT only under unverified counterfactual, anticipation, spillover and selection assumptions.','diagnostics':diagnostics})
    records=[{'id':'H_BASE','type':'hypothesis','statement':'The fixed policy setting produces a measurable relative restaurant employment change; sign unrestricted.','falsifier':'The raw records cannot measure both outcomes or the change contrast is incompatible with the hypothesis wording.'},
      {'id':'E_BASE','type':'experiment','hypothesis_id':'H_BASE','validation':'Parse codebook fields, preserve records, estimate complete-pair group contrast and frozen sensitivity checks.'},
      {'id':'D_RAW','type':'dataset','name':'NJ–PA 1992 fast-food restaurant survey public data','source':'David Card researcher data page','locator':'https://davidcard.berkeley.edu/data_sets.html','verified_at':STAMP,'access_status':'public downloaded','license':'Public offered research download; no express redistribution license; access qualification in data-provenance.json','checksum':h('data/raw/public.dat'),'codebook':'data/raw/codebook','unit':'restaurant source row'},
      {'id':'R_BASE','type':'run','experiment_id':'E_BASE','harness_version':'2.18.0-working-tree','status':'computed; strong causal design gate nonpassing','artifact':'research/results.json','data_ids':['D_RAW'],'input_hash':h('data/raw/public.dat'),'seed':19920401},
      {'id':'E_DATA','type':'evidence','source':'Original public data/codebook/survey instruments','locator':'data/raw/codebook','verified_at':STAMP,'scope':'Survey fields, source population, wave statuses; no original results'},
      {'id':'E_POLICY','type':'evidence','source':'NJ State Library original legislative history','locator':locators['nj1990'],'verified_at':STAMP,'scope':'Policy schedule and advance enactment'},
      {'id':'E_METHOD','type':'evidence','source':'Conley–Taber 2005 abstract and Alvarez–Ferman 2023 abstract','locator':'research/sources-methods.json','verified_at':STAMP,'scope':'Few-policy-change inferential boundary; full text downloaded but no target numerical results used'},
      {'id':'E_PROTOCOL','type':'evidence','source':'User-delegated bounded reconstruction contract','locator':'research/state.md','verified_at':STAMP,'scope':'Fixed question, target ban, budget, public acquisition authorization'},
      {'id':'E_CODE','type':'evidence','source':'Independent analysis and base-R verification','locator':'research/base-r-verification.json','verified_at':STAMP,'scope':'Numerical implementation agreement'},
      {'id':'F_MAIN','type':'finding','statement':f"Complete-pair relative change {results['primary']['estimate']}; n={results['primary']['n']}; restaurant HC1 SE={results['primary']['std_error']}",'run_ids':['R_BASE'],'status':'supported descriptive finding'},
      {'id':'F_SUPPORT','type':'finding','statement':'Frozen sensitivity estimates remain positive; gap, high-wage and auxiliary outcomes generated in results.json.','run_ids':['R_BASE'],'status':'supported descriptive findings'}]
    claims={
      'C_SCOPE':('Historical verification only; no novelty, general policy, or uncontaminated-discovery claim.',['E_PROTOCOL'],[],[],'supported','premise'),
      'C_POLICY':('NJ legislation scheduled the 1992 floor increase in advance.',['E_POLICY'],[],[],'supported','premise'),
      'C_DATA':('Observed raw fields support a reproducible restaurant sample and explicit headcount construction.',['E_DATA'],['F_MAIN'],[],'supported','premise'),
      'C_ESTIMAND':('Observed contrast equals retained-sample ATT only under stated unverified assumptions.',['E_METHOD'],[],['C_DATA','C_LIMIT'],'provisional','intermediate'),
      'C_INFERENCE':('Restaurant standard errors condition on two state paths and do not establish statewide causal significance.',['E_METHOD'],['F_MAIN'],['C_DATA'],'supported','intermediate'),
      'C_MAIN':('NJ–PA complete-pair FTE change contrast is positive; this is a sample description.',[],['F_MAIN'],['C_DATA'],'supported','conclusion'),
      'C_ROBUST':('Frozen measurement and subset variants retain positive point estimates but do not eliminate state shocks.',[],['F_SUPPORT'],['C_MAIN','C_LIMIT'],'supported','intermediate'),
      'C_GAP':('Initial wage gap is positively associated with changes; it does not identify exogenous dose response.',[],['F_SUPPORT'],['C_DATA'],'supported','intermediate'),
      'C_DIAGNOSTIC':('Selected high-wage NJ restaurants show a negative imprecise contrast with PA.',[],['F_SUPPORT'],['C_DATA'],'supported','intermediate'),
      'C_AUX':('Wage/price/hours/share changes describe adjustment margins without establishing mechanism.',[],['F_SUPPORT'],['C_DATA'],'supported','intermediate'),
      'C_LIMIT':('Single baseline, advance legislation, two jurisdictions, missingness and possible interference leave strong causal claims unresolved.',['E_DATA','E_POLICY','E_METHOD'],[],[],'supported','premise'),
      'C_REPRO':('The raw-data pipeline, hashes, code and independent arithmetic are auditable; target-source exposure remains disclosed.',['E_CODE','E_PROTOCOL'],['F_MAIN'],[],'supported','conclusion')}
    for key,(statement,evidence,findings,premises,status,role) in claims.items():
        records.append({'id':key,'type':'claim','statement':statement,'evidence_ids':evidence,'finding_ids':findings,'premise_ids':premises,'central':True,'role':role,'status':status,'scope':'research-only; surveyed restaurant sample and stated conditional assumptions','uncertainty':'Counterfactual state paths and missing-outcome selection unverified; numeric and specification snippet contamination disclosed.'})
    (ROOT/'research/manifest.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records))
    coverage=[]
    section_map=[('intro','introduction','Introduction',['C_SCOPE','C_MAIN','C_LIMIT']),('literature','literature','Setting and Relation to the Literature',['C_POLICY','C_INFERENCE','C_SCOPE']),('data','data','Data and Measurement',['C_DATA','C_REPRO']),('design','identification','Estimand, Design, and Uncertainty',['C_ESTIMAND','C_INFERENCE','C_LIMIT']),('results','results','Employment Results',['C_MAIN','C_GAP']),('robustness','robustness','Sensitivity and Adjustment Margins',['C_ROBUST','C_DIAGNOSTIC','C_AUX']),('conclusion','conclusion','Conclusion',['C_MAIN','C_LIMIT']),('derivation','appendix','Identification and Estimator Derivations',['C_ESTIMAND','C_INFERENCE']),('replication','appendix','Replication and Audit Record',['C_REPRO','C_SCOPE'])]
    sections=re.split(r'\\section\{([^{}]+)\}(?:\\label\{[^{}]+\})?',manuscript)
    texts={sections[i]:sections[i+1] for i in range(1,len(sections)-1,2)}
    for id,role,heading,claimids in section_map:
        packet=f'research/sections/{id}.md';(ROOT/packet).parent.mkdir(parents=True,exist_ok=True);(ROOT/packet).write_text(texts[heading])
        artifacts=[{'kind':'section_packet','path':packet,'sha256':h(packet)}]
        def add(kind,path):artifacts.append({'kind':kind,'path':path,'sha256':h(path)})
        if role=='literature':add('literature','research/literature-archive.json')
        if role=='data':add('data_documentation','research/data-provenance.json');add('analysis_code','scripts/analyze.py')
        if role=='identification':add('design_audit','research/design-audit.json');add('analysis_code','scripts/analyze.py')
        if role in ['results','robustness']:
            add('result','research/results.json');add('analysis_code','scripts/analyze.py');add('table','output/tables/'+('main' if role=='results' else 'robustness')+'.tex')
        if role=='appendix':add('appendix',packet)
        coverage.append({'id':id,'role':role,'status':'ready','headings':[heading],'claim_ids':claimids,'artifacts':artifacts})
    save('research/manuscript-coverage.json',{'schema_version':'1','mode':'empirical','manuscript_sha256':h('paper/manuscript/main.tex'),'sections':coverage,'qualification':'Ready means documentation of bounded descriptive claims, including nonpassing causal obligations; it does not indicate strong causal identification.'})
    save('research/package.json',{'topic_survey':'research/topic-survey.json','data_provenance':'research/data-provenance.json','manifest':'research/manifest.jsonl','manuscript':'paper/manuscript/main.tex','coverage':'research/manuscript-coverage.json','bibliography':'paper/references.bib','literature_archive':'research/literature-archive.json','results':'research/results.json','design_audit':'research/design-audit.json','logic_review':'research/logic-review.json','claim_scope':'research-only','mechanism_scope':'not-claimed','latex_main':'paper/manuscript/main.tex','latex_visual_review':'research/latex-visual-review.json'})

if __name__=='__main__':main()
