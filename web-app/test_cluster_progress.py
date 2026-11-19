"""Private running-pair metadata survives older comments and reordered manifests."""
import csv
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest
from slurmy_web.cluster_progress import current_calls
from slurmy_web.cluster import REMOTE_STATUS_SCRIPT


class ClusterProgressTests(unittest.TestCase):
    def test_old_comment_quoted_progress_and_reordered_string_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder);job=home/'slurmy/jobs/example';(job/'progress').mkdir(parents=True)
            with (job/'progress/batch_000003.csv').open('w',newline='') as stream:
                csv.writer(stream,quoting=csv.QUOTE_ALL).writerow(['running',7,1,2,0])
            with (job/'submission.csv').open('w',newline='') as stream:
                csv.writer(stream).writerows([['slurm_job_id','offset','array_size','batch_id'],['1234','3','1','3']])
            definition=dict(task_id='7',solver='Vampire configuration',problem='/Problems/SET/SET_002^3.p',cores=15)
            (job/'manifest.jsonl').write_text(json.dumps(definition)+'\n')
            line=f'1234_0|tester|example|RUNNING|1|15|1|60|n1||{job}|slurmy:v1:calls=8:batches=4'
            values=list(current_calls([line],home))
            self.assertEqual(len(values),1)
            self.assertEqual(values[0][:2],('1234_0',7))
            self.assertEqual(values[0][2]['solver'],'Vampire configuration')
            self.assertEqual(values[0][2]['problem'],'/Problems/SET/SET_002^3.p')
            self.assertEqual(values[0][2]['batch_id'],3)
            # Exercise exactly the embedded reader used by SSH and REST, not a separate code path.
            reader=REMOTE_STATUS_SCRIPT.split("printf 'CALLS\\n'",1)[1].split("printf 'METADATA\\n'",1)[0]
            result=subprocess.run(['bash','-c','jobs='+shlex.quote(line)+'\n'+reader],env={**os.environ,'HOME':folder},capture_output=True,text=True,check=True)
            self.assertTrue(result.stdout.startswith('1234_0|7|'))
            # Queue entries outside the connected user's direct job tree are never read.
            self.assertEqual(list(current_calls([line.replace(str(job),'/other/home/slurmy/jobs/example')],home)),[])
