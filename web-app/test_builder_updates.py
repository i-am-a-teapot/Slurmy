"""Workflow defaults, copying source globs, and remote axiom validation."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from slurmy_web import workflows
from slurmy_web.app import create_app
from slurmy_web import batch_suggestion as batch

class BuilderUpdateTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name);self.workflow=self.root/'sample';self.workflow.mkdir()
        (self.workflow/'Makefile').write_text('')
        for name,value in [('USER_RUNS',self.root),('BASE',self.root)]:
            p=patch.object(workflows,name,value);p.start();self.addCleanup(p.stop)
        with patch.object(workflows,'migrate_user_runs'):self.client=create_app().test_client()
        with self.client.session_transaction() as session:session['csrf']='test'

    def test_new_editor_has_implicit_solver_mode_and_default_fifty(self):
        response=self.client.get('/new')
        self.assertEqual(response.status_code,200)
        self.assertIn(b'type="hidden" name="mode" value="interactive"',response.data)
        self.assertNotIn(b'How do you want to define',response.data)
        self.assertIn(b'name="max_outstanding" type="number" min="1" step="1" value="50"',response.data)
        self.assertNotIn(b'id="path-go"',response.data)
        self.assertIn(b'id="batch-explanation-dialog"',response.data)
        self.assertNotIn(b'name="axiom_mode"',response.data)
        self.assertNotIn(b'Custom axiom globs',response.data)
        self.assertIn(b'tptp://TPTP-v10.0.0/Axioms/**/*.ax',response.data)
        self.assertIn(b'Add another axiom source',response.data)

    def test_copy_problem_sources_preserves_uri_and_deduplicates(self):
        glob='tptp://TPTP-v10.0.0/Problems/SET/*.p'
        with patch.object(workflows,'decisions',return_value=dict(globs=[glob,glob,'/tmp/local/*.p'])):
            response=self.client.get('/api/problem-sources',query_string=dict(directory=str(self.workflow)))
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json['globs'],[glob,'/tmp/local/*.p'])

    def test_copy_problem_sources_keeps_distinct_filename_selections(self):
        glob='tptp://TPTP-v10.0.0/Problems/SET/*.p'
        with patch.object(workflows,'decisions',return_value=dict(globs=[glob,glob,glob],problem_selections=['A.p','B.p','A.p'])):
            response=self.client.get('/api/problem-sources',query_string=dict(directory=str(self.workflow)))
        self.assertEqual(response.json['globs'],[glob,glob])
        self.assertEqual(response.json['problem_selections'],[['A.p'],['B.p']])

    def test_cluster_axiom_validation_does_not_convert_uri_to_local_path(self):
        uri='tptp://TPTP-v9.2.1/Axioms/SET*.ax'
        with patch('slurmy_archives.expand_axiom_source',return_value=[(Path('tptp:/share/datasets/TPTP/TPTP-v9.2.1/Axioms/SET001.ax'),Path('SET001.ax'))]) as expand:
            response=self.client.post('/api/validate-path?host=datalab',json=dict(kind='glob',role='axiom',value=uri),headers={'X-CSRF-Token':'test'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json['path'],uri);self.assertEqual(response.json['count'],1)
        self.assertEqual(expand.call_args.args[:2],(uri,'datalab'))

    def test_copy_axiom_sources_preserves_sources_and_supports_implicit_cluster_defaults(self):
        glob='tptp://TPTP-v9.2.1/Axioms/SET*.ax'
        for sources,expected in [([glob,glob,'/tmp/local/*.ax'],[glob,'/tmp/local/*.ax']),
                                 ([],['tptp://TPTP-v10.0.0/Axioms/**/*.ax'])]:
            with self.subTest(sources=sources), patch.object(workflows,'decisions',return_value=dict(axiom_globs=sources)):
                response=self.client.get('/api/axiom-sources',query_string=dict(directory=str(self.workflow)))
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json['globs'],expected)

    def test_unified_suggestion_uses_both_balancing_and_actual_batch_groups(self):
        node=dict(sockets=2,cores_per_socket=32,threads_per_core=1)
        config=dict(cores=1,threads_per_core=1,solver_name='A',command='./solver {{problem}}',cpu_limit=1,wc_limit=1,mem_limit='100MiB')
        nodes=batch.Topology([node]*10,active_tasks=10)
        with patch.object(batch,'partition_nodes',return_value=nodes),patch.object(workflows,'problem_glob',return_value=('pattern',[str(i) for i in range(1000)])):
            result=batch.suggest(dict(host='datalab',partition='CPU-amd',mode='interactive',configurations=[config,{**config,'solver_name':'B'}],globs=['pattern'],max_outstanding=50,pair_order='solver-major'))
        self.assertEqual(result['balance_batch_size'],40)
        self.assertEqual(result['fit_batch_size'],50)
        self.assertEqual(result['batch_size'],50)
        self.assertEqual(result['suggested_batches'],40)
        self.assertEqual(result['recommended_batch_size'],result['batch_size'])
        self.assertTrue(result['suggested_fits'])
