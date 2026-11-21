import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from blind_agent_turn import run_turn
from score_reconstruction import adjudicate, rubric_rows


class ReconstructionTurns(unittest.TestCase):
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
