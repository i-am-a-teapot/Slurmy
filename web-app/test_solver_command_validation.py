"""Validate solver executable paths locally without running command text."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from slurmy_web import workflows
from slurmy_web.app import create_app


class SolverCommandValidationTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.executable=self.root/'solver with spaces';self.executable.write_text('#!/bin/sh\nexit 0\n');self.executable.chmod(0o755)

    def test_missing_executable_is_rejected_but_future_cluster_build_is_allowed(self):
        with self.assertRaisesRegex(ValueError,'Solver executable does not exist'):
            workflows.validate_solver_command('./missing {{problem}}',str(self.root))
        result=workflows.validate_solver_command('./missing {{problem}}',str(self.root),True)
        self.assertIn('cluster build',result['message'])
        self.assertEqual(result['path'],str(self.root/'missing'))
        with self.assertRaisesRegex(ValueError,'does not exist'):
            workflows.validate_solver_command('/definitely-not-present/solver {{problem}}',str(self.root),True)

    def test_quoted_paths_permissions_and_nonexecution(self):
        result=workflows.validate_solver_command("'./solver with spaces' {{problem}}; touch forbidden",str(self.root))
        self.assertEqual(result['path'],str(self.executable))
        self.assertFalse((self.root/'forbidden').exists())
        self.executable.chmod(0o644)
        with self.assertRaisesRegex(ValueError,'not executable'):
            workflows.validate_solver_command("'./solver with spaces' {{problem}}",str(self.root))
        with self.assertRaisesRegex(ValueError,'not a file'):
            workflows.validate_solver_command(str(self.root),str(self.root))

    def test_http_validation_reports_missing_path_and_success_inline(self):
        with patch.object(workflows,'migrate_user_runs'):
            client=create_app().test_client()
        with client.session_transaction() as session:session['csrf']='test'
        def check(command,**extra):
            return client.post('/api/validate-solver-command',json=dict(command=command,directory=str(self.root),**extra),headers={'X-CSRF-Token':'test'})
        response=check('./missing {{problem}}')
        self.assertEqual(response.status_code,400,response.json)
        self.assertIn('does not exist',response.json['error'])
        self.assertEqual(check("'./solver with spaces' {{problem}}").status_code,200)
        self.assertEqual(check('./missing {{problem}}',build_on_cluster=True).status_code,200)
