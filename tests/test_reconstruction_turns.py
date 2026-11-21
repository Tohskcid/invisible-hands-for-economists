import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from blind_agent_turn import PLAN_LIMIT, run_turn
from run_reconstruction_batch import run as run_batch
from score_reconstruction import adjudicate, rubric_rows
from curate_benchmarks import sha
from verify_reconstruction_output import verify
from write_from_packet import write


class ReconstructionTurns(unittest.TestCase):
    def test_incomplete_data_author_keeps_work_without_a_submission(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet = root / 'q001'
            (packet / 'inputs').mkdir(parents=True)
            (packet / 'public-task.json').write_text('{}')
            (packet / 'inputs/input-1.csv').write_text('x\n1\n')
            names = ['public-task.json', 'inputs/input-1.csv']
            frozen = {'files': {'public/' + name: sha(packet / name) for name in names}}
            def interrupted(prompt, work, model, timeout):
                (work / 'analysis.py').write_text('partial work')
                raise subprocess.TimeoutExpired([], timeout)
            with patch('write_from_packet.verify_freeze', return_value=(frozen, 'id', names)), \
                    patch('write_from_packet.data_turn', side_effect=interrupted):
                with self.assertRaises(subprocess.TimeoutExpired):
                    write(root / 'frozen', packet, root / 'output', 'standard', 'model', 10)
            self.assertEqual((root / 'output/incomplete/analysis.py').read_text(), 'partial work')
            self.assertFalse((root / 'output/receipt.json').exists())

    def test_quota_stop_leaves_next_paper_pending(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / 'candidates.json'
            manifest.write_text(json.dumps({'cases': [{'id':'q001'}, {'id':'q002'}]}))
            output = root / 'runs'
            with patch('run_reconstruction_batch.process', side_effect=RuntimeError(PLAN_LIMIT)) as process:
                statuses = run_batch(manifest, output, 'model')
            self.assertEqual(process.call_count, 1)
            self.assertEqual(statuses['q001']['reason'], PLAN_LIMIT)
            self.assertFalse((output / 'q002').exists())

    def test_fractional_rubric_weights(self):
        rows = rubric_rows([{'id': 'A', 'max_score': 2.0}, {'id': 'B', 'max_score': 1.5}])
        self.assertEqual(rows['A']['allowed_scores'], [0, 1, 2])
        self.assertEqual(rows['B']['allowed_scores'], [0, 0.75, 1.5])

    def test_incomplete_second_pass_cannot_leave_a_verified_pdf(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            manuscript = root / 'manuscript.tex'
            manuscript.write_text('example')
            receipt = {'release_receipt_sha256': 'lock', 'output_sha256': {manuscript.name: sha(manuscript)}}
            (root / 'receipt.json').write_text(json.dumps(receipt))
            output = root / 'verified'
            output.mkdir()
            (output / 'manuscript.pdf').write_bytes(b'previous build')
            with patch('verify_reconstruction_output.verify_freeze', return_value=({}, 'lock', [])), \
                    patch('verify_reconstruction_output.subprocess.run',
                          side_effect=[subprocess.CompletedProcess([], 0), subprocess.TimeoutExpired([], 90)]):
                checks = verify(root / 'frozen', root, output)
            self.assertEqual(checks['tex_error'], 'TimeoutExpired')
            self.assertIsNone(checks['tex_exit'])
            self.assertFalse((output / 'manuscript.pdf').exists())

    def test_tool_activity_cannot_be_scored_as_blind(self):
        events = [{'type':'thread.started','thread_id':'test'},
                  {'type':'item.started','item':{'type':'command_execution'}}]
        result = subprocess.CompletedProcess([],0,'\n'.join(map(json.dumps,events)), '')
        with TemporaryDirectory() as tmp, patch('blind_agent_turn.account_environment',return_value={}), \
                patch('blind_agent_turn.subprocess.run',return_value=result):
            with self.assertRaisesRegex(ValueError,'unexpected tool activity'):
                run_turn('task',Path(tmp))

    def test_committed_scores_cannot_be_reused_on_revised_manuscript(self):
        rows=rubric_rows([{'id':'T','max_points':4,'criteria':[{'points':3,'criterion':'general proof'},
                                                              {'points':1,'criterion':'boundary'}]}])
        result={'items':{'T.1':{'score':1.5,'evidence':'Proof covers the restricted domain in Section 2.'},
                         'T.2':{'score':0,'evidence':'Boundary absent.'}},
                'summary':'Partial treatment','critical_errors':[]}
        with TemporaryDirectory() as tmp, patch('score_reconstruction.run_turn',return_value=(json.dumps(result),{})) as client:
            dest=Path(tmp)/'locked.json'
            saved=adjudicate('grade',rows,dest,'model',{'manuscript':'a'})
            self.assertEqual((saved['total'],saved['denominator']),(1.5,4))
            self.assertEqual(adjudicate('grade',rows,dest,'model',{'manuscript':'a'}),saved)
            with self.assertRaisesRegex(ValueError,'different evidence'):
                adjudicate('grade',rows,dest,'model',{'manuscript':'b'})
            self.assertEqual(client.call_count,1)


if __name__=='__main__':
    unittest.main()
