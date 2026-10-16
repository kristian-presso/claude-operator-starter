"""Tests for skills/always-on-mac/scripts/host_check.sh.

The script targets macOS, so each test builds a directory of stub commands (pmset,
fdesetup, defaults, launchctl, plutil, ...) that print what a real Mac would, puts it
first on PATH, and runs the script with HOST_CHECK_FORCE=1. Standard library only.
"""
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parent.parent / "skills" / "always-on-mac" / "scripts"
          / "host_check.sh")

GOOD = {
    "pmset": r'''case "$*" in
  "-g batt") echo "Now drawing from 'AC Power'";;
  "-g ps") echo "Now drawing from 'AC Power'";;
  "-g") printf ' SleepDisabled\t\t0\n sleep                0\n lowpowermode         0\n autorestart          1\n';;
esac''',
    "fdesetup": 'echo "FileVault is On."',
    "defaults": r'''case "$*" in
  *AutomaticallyInstallMacOSUpdates*) echo 0;;
  *CriticalUpdateInstall*) echo 1;;
esac''',
    "pgrep": "exit 0",
    "nc": "exit 0",
    "socketfilterfw": 'echo "Firewall is enabled. (State = 1)"',
    "ifconfig": r'''printf 'en0: flags=8863\n\tinet 192.168.1.5\nutun4: flags=8051\n\tinet 100.101.1.2 --> 100.101.1.2\n' ''',
    "claude": 'case "$1" in auth) exit 0;; esac',
    "plutil": r'''key="$2"; f="$5"
case "$key" in
  Label) basename "$f" .plist;;
  EnvironmentVariables.PATH) exit 1;;
  ProgramArguments.0) echo "$WRAPPER";;
esac''',
    "launchctl": r'''printf 'state = not running\n\tlast exit code = 0\n' ''',
    "crontab": "exit 1",
    "sysctl": "echo 1",
    "df": r'''printf 'Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/disk3 1000 400 600 40%% /System/Volumes/Data\n' ''',
    "tmutil": 'echo "Name          : Backup"',
    "id": r'''case "$1" in -Gn) echo "staff everyone";; -un) echo agent;; -u) echo 501;; esac''',
}


class HostCheckTest(unittest.TestCase):
    def run_check(self, overrides=None, agents=("com.example.nightly",), args=()):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            bindir = tmp / "bin"
            bindir.mkdir()
            home = tmp / "home"
            (home / "Library" / "LaunchAgents").mkdir(parents=True)
            for label in agents:
                (home / "Library" / "LaunchAgents" / f"{label}.plist").write_text("<plist/>")
            wrapper = tmp / "run-job.sh"
            wrapper.write_text('#!/bin/bash\nsource "$HOME/jobs/env.sh"\n')
            stubs = dict(GOOD, **(overrides or {}))
            for name, body in stubs.items():
                p = bindir / name
                p.write_text("#!/bin/bash\n" + body + "\n")
                p.chmod(p.stat().st_mode | stat.S_IEXEC)
            env = {
                "PATH": f"{bindir}:/usr/bin:/bin",
                "HOME": str(home),
                "HOST_CHECK_FORCE": "1",
                "SOCKETFILTERFW": str(bindir / "socketfilterfw"),
                "WRAPPER": str(wrapper),
            }
            out = subprocess.run(["bash", str(SCRIPT), *args], capture_output=True, text=True, env=env,
                                 timeout=30)
            return out.returncode, out.stdout

    def lines(self, stdout):
        rows = {}
        for line in stdout.splitlines():
            parts = line.split(None, 2)
            if len(parts) == 3 and parts[0] in ("PASS", "GAP", "MANUAL"):
                rows.setdefault(parts[1], []).append(parts[0])
        return rows

    def test_healthy_desktop_has_no_gaps(self):
        code, out = self.run_check()
        self.assertEqual(code, 0, out)
        self.assertIn("No gaps.", out)
        rows = self.lines(out)
        for check in ("security.filevault", "power.sleep", "power.autorestart", "jobs.path",
                      "claude.auth", "updates.auto-install", "host.disk"):
            self.assertEqual(rows.get(check), ["PASS"], f"{check}: {out}")

    def test_bare_path_job_is_a_gap(self):
        code, out = self.run_check({"plutil": GOOD["plutil"].replace('echo "$WRAPPER"', "echo /usr/local/bin/job")})
        self.assertEqual(code, 1)
        self.assertEqual(self.lines(out)["jobs.path"], ["GAP"])

    def test_low_power_mode_and_sleep_are_gaps(self):
        pm = GOOD["pmset"].replace("sleep                0", "sleep                10").replace(
            "lowpowermode         0", "lowpowermode         1")
        code, out = self.run_check({"pmset": pm})
        rows = self.lines(out)
        self.assertEqual(rows["power.sleep"], ["GAP"])
        self.assertEqual(rows["power.lowpower"], ["GAP"])
        self.assertEqual(code, 1)

    def test_laptop_asks_for_charge_limit_not_autorestart(self):
        pm = GOOD["pmset"].replace('"-g batt") echo "Now drawing from \'AC Power\'"',
                                   '"-g batt") echo " -InternalBattery-0 (id=1) 80%"')
        code, out = self.run_check({"pmset": pm})
        rows = self.lines(out)
        self.assertEqual(rows["power.charge-limit"], ["MANUAL"])
        self.assertNotIn("power.autorestart", rows)

    def test_signed_out_claude_and_failing_job(self):
        code, out = self.run_check({
            "claude": "exit 1",
            "launchctl": r'''printf 'state = not running\n\tlast exit code = 78\n' ''',
        })
        rows = self.lines(out)
        self.assertEqual(rows["claude.auth"], ["GAP"])
        self.assertEqual(rows["jobs.failing"], ["GAP"])
        self.assertEqual(code, 1)

    def test_unloaded_agent_is_a_gap(self):
        code, out = self.run_check({"launchctl": "exit 113"})
        self.assertIn("is not loaded", out)
        self.assertEqual(code, 1)

    def test_filevault_off_and_low_disk(self):
        code, out = self.run_check({
            "fdesetup": 'echo "FileVault is Off."',
            "df": r'''printf 'h\n/dev/disk3 1000 950 50 95%% /System/Volumes/Data\n' ''',
        })
        rows = self.lines(out)
        self.assertEqual(rows["security.filevault"], ["GAP"])
        self.assertEqual(rows["host.disk"], ["GAP"])

    def test_gaps_flag_hides_passes(self):
        _, full = self.run_check()
        self.assertIn("PASS", full)
        _, gaps = self.run_check(args=("--gaps",))
        self.assertNotIn("PASS ", gaps)
        self.assertIn("MANUAL", gaps)

    def test_refuses_other_os_without_force(self):
        out = subprocess.run(["bash", str(SCRIPT)], capture_output=True, text=True,
                             env={"PATH": "/usr/bin:/bin", "HOME": "/tmp"})
        self.assertEqual(out.returncode, 2)

    def test_never_calls_sudo(self):
        self.assertNotIn("sudo ", "\n".join(
            l for l in SCRIPT.read_text().splitlines()
            if not l.lstrip().startswith("#") and "say " not in l))


if __name__ == "__main__":
    unittest.main()
