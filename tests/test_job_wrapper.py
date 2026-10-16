"""Run the job wrapper from always-on-mac/references/scheduling-with-launchd.md as published.

The script is extracted from the markdown exactly as a reader would copy it. Standard
library only; needs bash and either flock or shlock (Linux has flock).
"""
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

DOC = (Path(__file__).resolve().parent.parent / "skills" / "always-on-mac" / "references"
       / "scheduling-with-launchd.md")


def wrapper_source() -> str:
    blocks = re.findall(r"```bash\n(.*?)```", DOC.read_text(encoding="utf-8"), re.S)
    return next(b for b in blocks if "run-job.sh" in b)


class JobWrapperTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        (self.home / "jobs" / "jobs").mkdir(parents=True)
        (self.home / "jobs" / "env.sh").write_text("export PATH=/usr/bin:/bin\n")
        (self.home / "jobs" / "run-job.sh").write_text(wrapper_source())

    def tearDown(self):
        self.tmp.cleanup()

    def job(self, body: str):
        p = self.home / "jobs" / "jobs" / "demo.sh"
        p.write_text("#!/bin/bash\n" + body + "\n")
        p.chmod(0o755)

    def run_wrapper(self):
        return subprocess.run(["bash", str(self.home / "jobs" / "run-job.sh"), "demo"],
                              env={"HOME": str(self.home), "PATH": "/usr/bin:/bin"},
                              capture_output=True, text=True, timeout=30)

    def outcomes(self):
        return (self.home / "jobs" / "outcomes" / "demo").read_text().splitlines()

    def test_records_reported_outcome(self):
        self.job("echo working; echo outcome=ok")
        self.assertEqual(self.run_wrapper().returncode, 0)
        self.assertIn("outcome=ok exit=0", self.outcomes()[-1])

    def test_exit_zero_without_outcome_is_unknown_not_ok(self):
        self.job("echo outcome=ok")
        self.run_wrapper()
        self.job("echo did nothing useful")
        self.run_wrapper()
        self.assertIn("outcome=unknown exit=0", self.outcomes()[-1])

    def test_failure_is_failed_and_exit_code_kept(self):
        self.job("echo boom; exit 3")
        self.assertEqual(self.run_wrapper().returncode, 3)
        self.assertIn("outcome=failed exit=3", self.outcomes()[-1])

    def test_model_failure_reported_despite_exit_zero(self):
        self.job("echo outcome=model_calls_failed; exit 0")
        self.run_wrapper()
        self.assertIn("outcome=model_calls_failed exit=0", self.outcomes()[-1])

    def test_log_keeps_history(self):
        self.job("echo first; echo outcome=ok")
        self.run_wrapper()
        self.job("echo second; echo outcome=no_work")
        self.run_wrapper()
        log = (self.home / "jobs" / "logs" / "demo.log").read_text()
        self.assertIn("first", log)
        self.assertIn("second", log)


if __name__ == "__main__":
    unittest.main()
