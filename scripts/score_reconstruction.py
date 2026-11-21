#!/usr/bin/env python3
"""Lock a standalone review before scoring a submitted paper against the frozen original."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import subprocess
from pathlib import Path
import tempfile

from blind_agent_turn import run_turn
from curate_benchmarks import read_record, require, sha, verify_freeze


QUALITY = ['Clarity of model, estimand and scope', 'Validity of central derivations or evidence',
           'Boundary cases and uncertainty', 'Economic interpretation and transparent limitations']


def rubric_rows(rows):
    items = {}
    for i, row in enumerate(rows, 1):
        if isinstance(row, str):
            row = {'id': str(i), 'criterion': row, 'max_score': 2}
        key = row['id']
        for j, part in enumerate(row.get('criteria', [row]), 1):
            name = f'{key}.{j}' if 'criteria' in row else key
            maximum = part.get('points', part.get('max_points', part.get('max_score', 2)))
            allowed = [0, maximum/2, maximum] if 'criteria' in row else list(range(maximum+1))
            require(name not in items and maximum > 0, 'invalid or duplicate rubric item')
            items[name] = {'criterion':part.get('criterion',part.get('dimension',row.get('title',name))),
                           'detail':part.get('evidence',row.get('scoring','')),
                           'allowed_scores':allowed}
        if 'criteria' in row:
            require(sum(p['points'] for p in row['criteria'])==row['max_points'],'atom maxima do not match')
    require(bool(items),'empty rubric')
    return items


def adjudicate(prompt, rows, dest, model, context, images=()):
    req = (prompt + '\nScore all items, honoring the specified allowed points. Provide concrete manuscript '
           'locators and concise reasons, including omissions. Distinguish a defensible alternative from an '
           'incorrect inference. Use no tools. Return JSON only: {"items":{"<id>":{"score":0,"evidence":"..."}},'
           '"summary":"...","critical_errors":["..."],"recognition":"..."} . Compute no totals.\n' +
           json.dumps({'criteria':rows,'evidence':context},ensure_ascii=False))
    request_id = hashlib.sha256((req+'\n'+model+'\n'+'\n'.join(sha(x) for x in images)).encode()).hexdigest()
    if dest.exists():
        saved = read_record(dest)
        require(saved.get('request_sha256')==request_id,'saved score was for different evidence')
        return saved
    with tempfile.TemporaryDirectory() as tmp:
        text, receipt = run_turn(req,Path(tmp),images=images,model=model)
    if text.startswith('```') and text.endswith('```'):
        text='\n'.join(text.splitlines()[1:-1])
    response=json.loads(text)
    require(set(response['items'])==set(rows),'judge omitted or added rubric items')
    for key, item in response['items'].items():
        require(type(item['score']) in (int,float) and item['score'] in rows[key]['allowed_scores']
                and isinstance(item['evidence'],str) and item['evidence'].strip(),'invalid score or missing evidence')
    require(isinstance(response['critical_errors'],list) and isinstance(response['summary'],str),'missing judgment')
    saved={'request_sha256':request_id,'locked_utc':datetime.now(timezone.utc).isoformat(),
           'judge':receipt,'items':response['items'],'summary':response['summary'],
           'critical_errors':response['critical_errors'],'recognition':response.get('recognition'),
           'total':sum(x['score'] for x in response['items'].values()),
           'denominator':sum(max(x['allowed_scores']) for x in rows.values())}
    with dest.open('x') as stream:
        json.dump(saved,stream,indent=2,ensure_ascii=False)
        stream.write('\n')
    return saved


def score(frozen, submission, output, quality_file=None, model='gpt-6.2-astra', phase='both'):
    _, commitment, _ = verify_freeze(frozen, frozen.name)
    author=read_record(submission/'receipt.json')
    require(author['release_receipt_sha256']==commitment,'author worked on a different freeze')
    require('manuscript.tex' in author['output_sha256'], 'missing committed manuscript')
    for name,val in author['output_sha256'].items():
        require(name in ('manuscript.tex','analysis.py','results.json') and val==sha(submission/name),
                'unexpected or changed author deliverable')
    context={'task':read_record(frozen/'public/public-task.json'),'manuscript':(submission/'manuscript.tex').read_text()}
    for name in ['analysis.py','results.json']:
        if name in author['output_sha256']:
            context[name]=(submission/name).read_text()
    output.mkdir(exist_ok=True,parents=True)
    rules=read_record(quality_file) if quality_file else {'rows':QUALITY,'anchors':'0 absent or incorrect, 1 incomplete, 2 sound.'}
    quality=adjudicate('Assess the paper as an answer to the public question. No reference comparison. '+
                       json.dumps(rules.get('anchors','')),rubric_rows(rules['rows']),output/'quality.json',model,context)
    if phase == 'quality':
        return {'quality':[quality['total'],quality['denominator']]}
    # Reference evidence never enters the standalone quality turn.
    c=read_record(frozen/'sealed/curation.json')
    context['source_reading']={s['id']:s['reading'] for s in c['sources']}
    context['source_limits']=c.get('source_limit',c.get('gaps',[]))
    context['quality_lock_sha256']=sha(output/'quality.json')
    order='Score historical coverage against the frozen original reading record and rubric. '+str(c.get('scoring',''))
    context['original_text'] = {}
    with tempfile.TemporaryDirectory() as tmp:
        images = []
        for source in c['sources']:
            pdf = frozen/'sealed/sources'/(source['id']+'.pdf')
            text = subprocess.check_output(['pdftotext','-layout',str(pdf),'-']).decode()
            context['original_text'][source['id']] = text
            pages = text.split('\f')
            if not pages[-1]:
                pages.pop()
            for number, page in enumerate(pages,1):
                if len(page.strip()) > 350:
                    continue
                stem = Path(tmp)/(source['id']+'-'+str(number))
                subprocess.run(['pdftoppm','-f',str(number),'-l',str(number),'-singlefile','-scale-to','1700',
                                '-jpeg',str(pdf),str(stem)],check=True,capture_output=True)
                images.append(stem.with_suffix('.jpg'))
        fidelity=adjudicate(order,rubric_rows(c['rubric']),output/'fidelity.json',model,context,images)
    return {'quality': [quality['total'], quality['denominator']],
            'fidelity': [fidelity['total'], fidelity['denominator']],
            'met_frozen_rubric': fidelity['total'] == fidelity['denominator'] and not c.get('gaps')
            and not quality['critical_errors'] and not fidelity['critical_errors'],
            'data_replay': 'independent replay required' if 'analysis.py' in author['output_sha256'] else 'no dataset'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('frozen','submission','output'):
        p.add_argument(name,type=Path)
    p.add_argument('--quality-rubric',type=Path)
    p.add_argument('--phase',choices=('quality','both'),default='both')
    p.add_argument('--model',default='gpt-6.2-astra')
    a=p.parse_args()
    print(json.dumps(score(a.frozen,a.submission,a.output,a.quality_rubric,a.model,a.phase)))


if __name__=='__main__':
    main()
