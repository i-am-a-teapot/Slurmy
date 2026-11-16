"""Run the real result publisher with solver-enforced limits and normal results."""
import csv
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import tarfile
import szs
import unittest

TEMPLATES=Path(__file__).parent/'templates'


class SolverLimitTests(unittest.TestCase):
    def run_pair(self, output, expected, code=1, stderr=False, computer_info=False, timestamp=False, info_exit=0):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in ['calls/0','rootfs/runtime','results/index','progress']:(root/name).mkdir(parents=True)
            shutil.copy2(TEMPLATES/'csv.sh',root/'csv.sh')
            (root/'szs.sh').write_text(szs.shell_library())
            (root/'calls/0/config.sh').write_text('TASK_ID=0\nTASK_KEY=abcdef\nCORES=1\nTHREADS_PER_CORE=1\nWC_LIMIT=3\nSOLVER_ROOT_REL=runtime\n')
            with (root/'calls/0/config.sh').open('a') as config:
                config.write(f'GET_COMPUTER_INFO={int(computer_info)}\nCOMPUTER_INFO_TIMESTAMP={int(timestamp)}\nCPU_LIMIT=2\nMEM_LIMIT_MIB=100\n')
            (root/'GetComputerInfo').write_text('''#!/bin/bash
printf '%s\\n' "$@" > "$JOB_DIR/info-arguments"
if [[ " $* " == *' --timestamp '* ]]; then printf '0.00/0.00\\t'; fi
printf '%% Computer : test-node\\n'
exit '''+str(info_exit)+'\n')
            (root/'payload').write_text(output)
            (root/'timed_call.sh').write_text('''#!/bin/bash
cp "$JOB_DIR/payload" "${'''+('SOLVER_STDERR_LOG' if stderr else 'SOLVER_LOG')+'''}"
touch "$SOLVER_LOG" "$SOLVER_STDERR_LOG"
printf 'TIMEOUT=false\\nMEMOUT=false\\nWCTIME=1.01\\nCPUTIME=0.9\\n' > "$VAR_FILE"
printf 'Child status: '''+str(code)+'''\\n' > "$WATCHER_LOG"
exit '''+str(code)+'\n')
            result=subprocess.run(['bash',str(TEMPLATES/'call.sh'),'0','0'],env={**os.environ,'JOB_DIR':str(root)},capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            with (root/'results/batch_000000_task_000000000.csv').open() as stream:row=next(csv.DictReader(stream))
            self.assertEqual(row['status'],expected)
            self.assertEqual(row['complete'],'true')
            with tarfile.open(root/'results'/row['archive']) as archive:
                solver_log = next(item for item in archive.getmembers() if item.name.endswith('.solver.log'))
                text = archive.extractfile(solver_log).read().decode()
                self.assertFalse(any(item.name.endswith('computer-info.header') for item in archive.getmembers()))
                if computer_info:
                    self.assertTrue(text.startswith(('0.00/0.00\t' if timestamp else '')+'% Computer : test-node\n'), text)
                    arguments = (root/'info-arguments').read_text().splitlines()
                    self.assertEqual('--timestamp' in arguments, timestamp)
                    self.assertIn('100MiB', arguments)
                    if info_exit:
                        diagnostic = next(item for item in archive.getmembers() if item.name.endswith('.controller.log'))
                        self.assertIn('continuing with the solver', archive.extractfile(diagnostic).read().decode())
                else:
                    self.assertFalse((root/'info-arguments').exists())
            return row

    def test_computer_information_survives_solver_log_truncation_and_matches_timestamps(self):
        for timestamp in (False, True):
            self.run_pair('% SZS status Theorem\n', 'ok', code=0, computer_info=True, timestamp=timestamp)

    def test_computer_information_failure_does_not_prevent_solver_execution(self):
        self.run_pair('% SZS status Theorem\n', 'ok', code=0, computer_info=True, info_exit=1)

    def test_every_official_status_is_published_with_full_name_and_correct_execution_outcome(self):
        for name,code in szs.STATUSES.items():
            for value in (name,code):
                with self.subTest(value=value):
                    row=self.run_pair('% SZS status '+value+'\n', szs.execution_status(name),code=0)
                    self.assertEqual(row['szs_status'],name)
        row=self.run_pair('% szs STATUS ASS(TMO,THM)\n','no-success',code=0)
        self.assertEqual(row['szs_status'],'Assumed(Timeout,Theorem)')

    def test_vampire_internal_timeout_on_stdout_or_stderr(self):
        for stderr in (False,True):
            with self.subTest(stderr=stderr):
                row=self.run_pair('0.80/1.00\t% Termination reason: Time limit\n','time-limit',stderr=stderr)
                self.assertEqual(row['timed_out'],'true')

    def test_szs_internal_limits_set_resource_flags(self):
        row=self.run_pair('% SZS status Timeout\n','time-limit');self.assertEqual(row['timed_out'],'true')
        row=self.run_pair('% SZS status MemoryOut\n','memory-limit');self.assertEqual(row['memory_out'],'true')
        row=self.run_pair('% Termination reason: Memory limit\n','memory-limit');self.assertEqual(row['memory_out'],'true')

    def test_unrelated_text_and_success_are_not_overridden(self):
        self.run_pair('syntax error around Time limit\n','solver-error')
        row=self.run_pair('% Termination reason: Time limit\n% SZS status Theorem\n','ok',code=0)
        self.assertEqual(row['timed_out'],'false');self.assertEqual(row['szs_status'],'Theorem')
