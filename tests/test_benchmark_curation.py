import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import curate_benchmarks as gate
import read_benchmarks as reader


def write(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record))


class BenchmarkCurationTests(unittest.TestCase):
    def test_nested_file_findings_preserve_each_section(self):
        review = {'decision': 'hold', 'sufficiency': 'missing primitive', 'leakage': 'no answer',
                  'input_findings': {'public-task.json': {'question': 'clear', 'model': 'missing distribution'}}}
        actual = reader.decision(review, ['public-task.json'])
        self.assertEqual(actual['input_findings']['public-task.json'], 'question: clear\nmodel: missing distribution')

    def test_entire_large_numeric_input_is_reviewed_and_copied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv = root / 'observations.csv'
            csv.write_text('group,x\n' + '1,0\n' * 50000 + '2,\n')
            stage = root / 'staging'
            stage.mkdir()
            name = 'inputs/input-1.csv'
            asset = {'file': csv.name, 'sha256': gate.sha(csv), 'provenance': 'Original observation rows.',
                     'columns': {'group': 'Original study ID.', 'x': 'Observed value.'}}
            _, evidence = reader.input_evidence(root, {'inputs': {name: asset}}, stage)
            self.assertEqual((stage / name).read_bytes(), csv.read_bytes())
            self.assertEqual(evidence[name]['rows'], 50001)
            self.assertEqual(evidence[name]['columns']['group']['levels'], [1, 2])
            self.assertEqual(evidence[name]['columns']['x']['missing'], 1)
            with csv.open('a') as stream:
                stream.write('3,hidden-text\n')
            asset['sha256'] = gate.sha(csv)
            with self.assertRaisesRegex(ValueError, 'row 50002'):
                reader.input_evidence(root, {'inputs': {name: asset}}, stage)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'private'
        self.author = Path(self.temp.name) / 'author'
        self.manifest = self.root / 'batch.json'
        self.case = self.root / 'cases/q001'
        self.case.mkdir(parents=True)
        write(self.manifest, {'cases': ['cases/q001']})
        self.pdf = self.root / 'original.pdf'
        self.pdf.write_bytes(b'%PDF-example')
        self.info = patch('curate_benchmarks.subprocess.run').start()
        self.addCleanup(patch.stopall)
        self.info.return_value.stdout = b'Pages: 3\n'
        self.info.return_value.returncode = 0
        self.source = {'id': 'main', 'role': 'main', 'file': 'original.pdf', 'sha256': gate.sha(self.pdf),
                       'url': 'https://example.org/original.pdf', 'version': 'typeset', 'identity_check': 'byline and issue',
                       'reading': [{'pages': [1, 2], 'note': 'Primitives then objectives'},
                                   {'pages': [3, 3], 'note': 'Embedded derivation', 'appendix': True}]}
        self.public = {'id': 'q001', 'mode': 'theory', 'question': 'Which allocations are feasible?',
                       'conditions': {'goods': 'One divisible good.'}, 'available_inputs': [],
                       'required_outputs': ['Characterize the feasible set.'], 'source_restrictions': 'Use this packet.',
                       'neutrality_obligation': 'Justify conclusions.'}
        mapping = {'source': 'main', 'pages': [1, 2], 'reason': 'Defines the allocation problem.'}
        self.curation = {'target': {'title': 'Distinctive Private Original', 'authors': ['Ada Q. Researcher'],
                                    'doi': '10.1234/private'}, 'curator': 'researcher A', 'sources': [self.source],
                         'appendix_status': 'embedded', 'appendix_check': 'Last original page contains the appendix.',
                         'field_sources': {'question': mapping, 'conditions.goods': mapping},
                         'withheld': ['Closed-form allocation'], 'rubric': ['Characterization'],
                         'contamination': 'Unusual primitive is recognizable', 'gaps': [], 'input_checks': {}}
        self.update()

    def update(self):
        write(self.case / 'public-task.json', self.public)
        write(self.case / 'curation.json', self.curation)

    def run_gate(self, cmd):
        return gate.batch(cmd, self.manifest, self.author if cmd == 'export' else None)['q001']

    def review(self):
        inspected = self.run_gate('inspect')
        self.assertEqual(inspected['status'], 'inspected', inspected)
        record = {'reviewer': 'reviewer B', 'decision': 'pass',
                  'sufficiency': 'The goods and feasibility goal are explicit.',
                  'leakage': 'Neither the allocation formula nor the title appear in the packet.',
                  'input_findings': {n: 'Content and coverage inspected' for n in inspected['author_files']},
                  'checked_sha256': inspected['checked_sha256']}
        write(self.case / 'review.json', record)
        return record

    def test_immutable_freeze_and_clean_idempotent_export(self):
        self.review()
        (self.case / 'secret-answers.txt').write_text('hidden')
        frozen = self.run_gate('freeze')
        self.assertEqual(frozen['status'], 'frozen', frozen)
        self.assertEqual(frozen, self.run_gate('freeze'))
        exported = self.run_gate('export')
        self.assertEqual(exported['status'], 'exported', exported)
        self.assertEqual(exported, self.run_gate('export'))
        self.assertEqual(list((self.author / 'q001').iterdir()), [self.author / 'q001/public-task.json'])
        self.public['required_outputs'].append('Additional result')
        self.update()
        self.assertIn('review hashes differ', self.run_gate('freeze')['reason'])
        self.review()
        self.assertIn('already frozen', self.run_gate('freeze')['reason'])
        self.assertEqual(exported, self.run_gate('export'))
        (self.author / 'q001/private').mkdir()
        self.assertIn('unexpected directory', self.run_gate('export')['reason'])

    def test_no_release_on_partial_coverage_hash_error_or_opaque_proof_inputs(self):
        self.source['reading'][0]['pages'] = [2, 2]
        self.update()
        self.assertIn('unlogged page 1', self.run_gate('inspect')['reason'])
        self.source['reading'][0]['pages'] = [1, 2]
        self.curation['appendix_status'] = 'none'
        self.update()
        self.assertIn('appendix inventory', self.run_gate('inspect')['reason'])
        self.curation['appendix_status'] = 'embedded'
        del self.curation['field_sources']['conditions.goods']
        self.update()
        self.assertIn('page mapping', self.run_gate('inspect')['reason'])
        self.curation['field_sources']['conditions.goods'] = self.curation['field_sources']['question']
        self.curation['gaps'] = ['The indispensable lemma uses an undisclosed primitive.']
        self.update()
        self.review()
        self.assertIn('unresolved gaps', self.run_gate('freeze')['reason'])
        self.pdf.write_bytes(b'%PDF-other')
        self.assertIn('SHA-256', self.run_gate('inspect')['reason'])

    def test_leakage_in_json_and_inputs_and_review_binding(self):
        for text in ['10.1234/private', 'Ada Q. Researcher', 'Distinctive Private Original', 'https://example.org/foo']:
            self.public['question'] = text
            self.update()
            self.assertEqual(self.run_gate('inspect')['status'], 'blocked')
        self.public['question'] = 'Which sets?'
        self.public['answer_key'] = 'solution'
        self.update()
        self.assertIn('unapproved fields', self.run_gate('inspect')['reason'])
        del self.public['answer_key']
        self.public['available_inputs'] = ['inputs/input-001.csv']
        self.public['mode'] = 'empirical'
        self.public['data_access_status'] = 'The observations are supplied; the older survey is unavailable.'
        self.curation['track'] = 'calibration'
        self.curation['input_checks'] = {'inputs/input-001.csv': 'Verified released public observations.'}
        self.curation['gaps'] = ['Older survey missing']
        self.curation['rubric'] = [{'id': 'survey', 'criterion': 'Replicate older survey', 'max_score': 2,
                                   'scoring': 'No evidence 0; partial 1; full 2'}]
        self.curation['calibration'] = {'feasible_scope': 'Analyze supplied observations',
                                        'missing_blocks': {'Older survey missing': 'survey'}}
        self.update()
        data = self.case / 'inputs/input-001.csv'
        data.parent.mkdir()
        data.write_text('title\nDistinctive Private Original')
        self.assertIn('target identifier', self.run_gate('inspect')['reason'])
        data.write_text('x,y\n0,1\n')
        review = self.review()
        self.assertEqual(self.run_gate('freeze')['status'], 'frozen')
        data.write_text('x,y\n1,1\n')
        self.assertIn('review hashes differ', self.run_gate('freeze')['reason'])
        review['reviewer'] = 'researcher A'
        write(self.case / 'review.json', review)
        self.assertIn('independent', self.run_gate('freeze')['reason'])
        self.curation['track'] = 'strict-historical'
        self.update()
        self.assertIn('timeline', self.run_gate('inspect')['reason'])

    def test_tampered_frozen_packet_and_path_escapes(self):
        self.review()
        self.run_gate('freeze')
        pub = self.root / 'frozen/q001/public/public-task.json'
        pub.chmod(0o600)
        pub.write_text(json.dumps({**self.public, 'question': 'Different?'}))
        self.assertIn('SHA-256 mismatch', self.run_gate('export')['reason'])
        self.assertFalse((self.author / 'q001').exists())
        self.source['file'] = '../original.pdf'
        self.update()
        self.assertIn('unsafe relative path', self.run_gate('inspect')['reason'])
        self.source['file'] = 'linked.pdf'
        (self.root / 'linked.pdf').symlink_to(self.pdf)
        self.update()
        self.assertIn('symlink', self.run_gate('inspect')['reason'])
        with self.assertRaisesRegex(ValueError, 'outside'):
            gate.batch('export', self.manifest, self.root / 'author')
        self.author.rmdir()
        self.author.symlink_to(self.root)
        with self.assertRaisesRegex(ValueError, 'separate'):
            gate.batch('export', self.manifest, self.author)

    def test_strict_data_requires_exact_historical_vintage_and_independent_file(self):
        filename = 'inputs/input-001.csv'
        data = self.case / filename
        data.parent.mkdir()
        data.write_text('year,count\n1990,5\n')
        self.public.update(mode='empirical', available_inputs=[filename])
        self.curation['input_checks'] = {filename: 'Archived survey of counts.'}
        targets = {'first_target_public_at': '1992-02-01', 'first_journal_public_at': '1993-01-01',
                   'target_date_source': 'https://example.org/work', 'journal_date_source': 'https://example.org/journal'}
        source = {'title': filename, 'first_public_at': '1992', 'date_source': 'https://example.org/archive',
                  'is_target_version': False, 'author_material': True}
        self.curation['timeline'] = {'target': targets, 'comparators': [source]}
        self.update()
        self.assertIn('pre-target', self.run_gate('inspect')['reason'])
        source['first_public_at'] = '1991'
        source['is_target_version'] = True
        self.update()
        self.assertIn('pre-target', self.run_gate('inspect')['reason'])
        source['is_target_version'] = False
        self.update()
        self.review()
        self.assertEqual(self.run_gate('freeze')['status'], 'frozen')
        data.unlink()
        data.symlink_to(self.root / 'batch.json')
        self.assertIn('symlink', self.run_gate('inspect')['reason'])

    def test_automated_reader_holds_unreadable_page_without_publishing(self):
        candidate = {k: self.curation[k] for k in ('target', 'appendix_status', 'appendix_check')}
        candidate.update(id='q002', mode='theory', sources=[self.source])
        manifest = self.root / 'candidates.json'
        write(manifest, {'cases': [candidate]})
        batches = [('main', {1: ''}, ['image1'])]
        response = ({'pages': [{'page': 1, 'readable': False, 'appendix': False, 'note': 'table indiscernible'}]}, {})
        with patch.object(reader, 'page_batches', return_value=batches), patch.object(reader, 'ask', return_value=response), \
                patch.object(reader, 'reread_page', return_value=(response[0]['pages'][0], {})):
            result = reader.run(manifest, 'model')['q002']
        self.assertIn('requires visual review', result['reason'])
        self.assertFalse((self.case.parent / 'q002').exists())

    def test_numeric_audit_must_use_the_released_observations(self):
        table = self.root / 'observations.csv'
        table.write_text('x\n1\n')
        audit = self.root / 'calculation.json'
        write(audit, {'input_sha256': 'older edition'})
        candidate = {k: self.curation[k] for k in ('target', 'appendix_status', 'appendix_check')}
        name = 'inputs/input-1.csv'
        candidate.update(id='q002', mode='empirical', sources=[self.source],
                         inputs={name: {'file': table.name, 'sha256': gate.sha(table), 'provenance': 'Observed counts.'}},
                         numeric_audits=[{'input': name, 'file': audit.name, 'sha256': gate.sha(audit)}])
        manifest = self.root / 'candidates.json'
        write(manifest, {'cases': [candidate]})
        with patch.object(reader, 'ask') as ask:
            result = reader.run(manifest, 'model')['q002']
        self.assertIn('different observations', result['reason'])
        ask.assert_not_called()
        self.assertFalse((self.case.parent / 'q002').exists())

    def test_absent_observations_still_allow_a_private_sourced_question(self):
        candidate = {k: self.curation[k] for k in ('target', 'appendix_check')}
        candidate.update(id='q002', mode='empirical', sources=[self.source], appendix_status='unresolved',
                         pending_materials=['The underlying survey was not obtained.'])
        manifest = self.root / 'candidates.json'
        write(manifest, {'cases': [candidate]})
        pages = [('main', {1: 'text'}, ['image'])]
        loc = {'source': 'main', 'pages': [1, 1]}
        answers = [({'pages': [{'page': 1, 'readable': True, 'appendix': False, 'note': 'Survey population.'}]}, {}),
                   ({'question': 'How does employment vary?', 'conditions': {'population': 'Sampled workers.'},
                     'field_sources': {'question': loc, 'conditions.population': loc}, 'blocked_work':['Estimation.']}, {}),
                   ({'decision':'clear','finding':'The employment question gives no numerical or sign information.'}, {})]
        with patch.object(reader, 'page_batches', return_value=pages), patch.object(reader, 'ask', side_effect=answers) as ask:
            result = reader.run(manifest, 'model')['q002']
            self.assertEqual(reader.run(manifest, 'model')['q002'], result)
            self.assertEqual(ask.call_count, 3)
        self.assertEqual(result['status'], 'source-read-awaiting-materials')
        self.assertTrue((self.root / result['private_draft']).is_file())
        self.assertFalse((self.case.parent / 'q002').exists())

    def test_mixed_batch_finishes_good_cases(self):
        self.review()
        write(self.manifest, {'cases': ['cases/q002', 'cases/q001']})
        outcomes = gate.batch('freeze', self.manifest)
        self.assertEqual([v['status'] for v in outcomes.values()], ['blocked', 'frozen'])
        exported = gate.batch('export', self.manifest, self.author)
        self.assertEqual([v['status'] for v in exported.values()], ['blocked', 'exported'])

    def test_automated_reader_checks_all_pages_and_preserves_existing_cases(self):
        candidate = {k: self.curation[k] for k in ('target', 'appendix_status', 'appendix_check')}
        candidate.update(id='q001', mode='theory', sources=[{k: v for k, v in self.source.items() if k != 'reading'}])
        manifest = self.root / 'candidates.json'
        write(manifest, {'cases': [candidate]})
        self.assertEqual(reader.run(manifest, 'model')['q001']['status'], 'blocked')
        shutil.rmtree(self.case)
        seen = []
        def ask(_, label, prompt, images, model):
            seen.append(label)
            if label.startswith('read-'):
                return {'pages': [{'page': n, 'readable': True, 'appendix': n == 3, 'note': f'Facts page {n}'}
                                  for n in [1, 2, 3]]}, {'turn_id': 'read'}
            if label == 'extract':
                return {'public': self.public, 'private': self.curation}, {'turn_id': 'extract'}
            return {'decision': 'pass', 'sufficiency': 'All primitives supplied', 'leakage': 'Answer withheld',
                    'input_findings': {'public-task.json': 'No other inputs needed'}}, {'turn_id': 'review'}
        batches = [('main', {n: 'page' for n in [1, 2, 3]}, ['image1', 'image2', 'image3'])]
        with patch.object(reader, 'page_batches', return_value=batches), patch.object(reader, 'ask', side_effect=ask):
            first = reader.run(manifest, 'model')['q001']
            self.assertEqual(first['status'], 'review-pass', first)
            released_task = json.loads((self.case / 'public-task.json').read_bytes())
            self.assertEqual(released_task['required_outputs'], [reader.DELIVERABLE])
            self.assertEqual(first, reader.run(manifest, 'model')['q001'])
        self.assertEqual(seen, ['read-main-1', 'extract', 'review-main-1'])
        self.assertEqual(self.run_gate('freeze')['status'], 'frozen')

    def test_review_preserves_private_notes_and_requires_fresh_review_of_held_draft(self):
        candidate = {k: self.curation[k] for k in ('target', 'appendix_status', 'appendix_check')}
        candidate.update(id='q001', mode='theory', sources=[self.source])
        manifest = self.root / 'candidates.json'
        write(manifest, {'cases': [candidate]})
        batches = [('main', {1: 'first', 2: 'second', 3: 'appendix'}, [1, 2, 3])]
        shutil.rmtree(self.case)
        calls = []
        def answer(_, label, prompt, images, model):
            calls.append(label)
            if label.startswith('read-'):
                return {'pages': [{'page': n, 'readable': True, 'appendix': n == 3,
                                   'note': 'Specific source facts'} for n in (1, 2, 3)]}, {}
            if label in ('extract', 'revise'):
                self.public['question'] = 'Select the specified bound.' if label == 'extract' else 'Which bounds follow?'
                return {'public': dict(self.public), 'private': self.curation}, {}
            # The reviewer reports an extra, private source check in both passes.
            return {'decision': 'hold', 'sufficiency': 'Primitives explicit', 'leakage': 'Unresolved scope',
                    'input_findings': {'public-task.json': 'Goal needs repair', 'original': 'Appendix examined'}}, {}
        with patch.object(reader, 'page_batches', return_value=batches), patch.object(reader, 'ask', side_effect=answer):
            self.assertEqual(reader.run(manifest, 'm')['q001']['status'], 'review-hold')
            self.assertEqual(reader.run(manifest, 'm')['q001']['status'], 'review-hold')
        self.assertEqual(calls.count('review-main-1'), 2)
        self.assertEqual(calls.count('revise'), 1)
        archived = list((self.root / 'reader-work/q001').glob('held-*.json'))
        self.assertEqual(len(archived), 1)
        original = json.loads(archived[0].read_text())
        self.assertEqual(original['review']['other_evidence_findings'], {'original': 'Appendix examined'})
        self.assertNotEqual(original['public']['question'], json.loads((self.case / 'public-task.json').read_text())['question'])
        self.assertEqual(self.run_gate('freeze')['status'], 'blocked')


if __name__ == '__main__':
    unittest.main()
