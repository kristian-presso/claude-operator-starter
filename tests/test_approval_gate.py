"""Unit tests for scripts/approval_gate.py, the plugin's PreToolUse hook.

Standard library only. Run from the repository root or the plugin folder:

    python3 -m unittest discover -s tests -v

Each test runs the script as Claude Code does: JSON on stdin, decision JSON (or nothing)
on stdout, exit code 0.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
SCRIPT = PLUGIN / "scripts" / "approval_gate.py"


class GateCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name) / "project"
        self.project.mkdir()
        self.addCleanup(self.tmp.cleanup)

    # helpers -------------------------------------------------------------

    def run_raw(self, stdin: str, env_extra: dict | None = None) -> tuple[int, str, str]:
        env = {k: v for k, v in os.environ.items() if not k.startswith(("APPROVAL_GATE", "CLAUDE_PROJECT_DIR"))}
        env["CLAUDE_PROJECT_DIR"] = str(self.project)
        env.update(env_extra or {})
        res = subprocess.run(
            [sys.executable, "-I", str(SCRIPT)], input=stdin, capture_output=True,
            text=True, env=env, cwd=str(self.project), timeout=30,
        )
        return res.returncode, res.stdout, res.stderr

    def decide(self, tool: str, tool_input: dict, cwd: str | None = None):
        payload = {
            "session_id": "test", "hook_event_name": "PreToolUse", "tool_name": tool,
            "tool_input": tool_input, "cwd": cwd or str(self.project), "permission_mode": "default",
        }
        code, out, err = self.run_raw(json.dumps(payload))
        self.assertEqual(code, 0, err)
        if not out.strip():
            return None, ""
        data = json.loads(out)
        hso = data["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], "PreToolUse")
        return hso["permissionDecision"], hso["permissionDecisionReason"]

    def bash(self, command: str, cwd: str | None = None):
        return self.decide("Bash", {"command": command, "description": "x"}, cwd)

    def config(self, data) -> None:
        d = self.project / ".claude"
        d.mkdir(exist_ok=True)
        text = data if isinstance(data, str) else json.dumps(data)
        (d / "approval-gate.json").write_text(text, encoding="utf-8")

    def git_repo(self, branch: str) -> None:
        subprocess.run(["git", "init", "-q", "-b", branch, str(self.project)], check=True)

    def assertAsks(self, result, fragment: str = ""):
        decision, reason = result
        self.assertEqual(decision, "ask", reason)
        self.assertIn(fragment, reason)

    def assertSilent(self, result):
        self.assertEqual(result, (None, ""))


class Blocked(GateCase):
    """Calls that send, publish, pay or delete must come back as 'ask'."""

    def test_push_to_main_explicit(self):
        self.assertAsks(self.bash("git push origin main"), "pushes to main")

    def test_push_refspec_to_master(self):
        self.assertAsks(self.bash("git push origin HEAD:refs/heads/master"), "master")

    def test_bare_push_on_main_branch(self):
        self.git_repo("main")
        self.assertAsks(self.bash("git push"), "pushes to main")

    def test_force_push_any_branch(self):
        self.assertAsks(self.bash("git push -f origin feature/x"), "force-pushes")
        self.assertAsks(self.bash("git push --force-with-lease origin feature/x"), "force-pushes")

    def test_push_hidden_in_compound_command(self):
        self.assertAsks(self.bash("npm test && git add -A && git commit -m wip && git push origin main"))

    def test_push_with_git_dash_c_and_env(self):
        self.assertAsks(self.bash("GIT_TRACE=1 git -C ../other push origin main"))

    def test_push_inside_bash_dash_c(self):
        self.assertAsks(self.bash("bash -c 'git push origin main'"))

    def test_npm_publish(self):
        self.assertAsks(self.bash("npm publish --access public"), "publishes a package")

    def test_other_package_publishers(self):
        for cmd in ("pnpm publish", "cargo publish", "twine upload dist/*", "gh release create v1.0.0"):
            with self.subTest(cmd=cmd):
                self.assertAsks(self.bash(cmd), "publishes")

    def test_rm_rf_outside_project(self):
        self.assertAsks(self.bash("rm -rf /tmp/somewhere"), "outside the project")
        self.assertAsks(self.bash("rm -rf ~/Documents"), "outside the project")
        self.assertAsks(self.bash("rm -fr ../sibling"), "outside the project")

    def test_rm_rf_whole_project(self):
        self.assertAsks(self.bash("rm -rf ."), "whole project")
        self.assertAsks(self.bash("rm -rf ./*"), "whole project")

    def test_rm_rf_unresolvable_variable(self):
        self.assertAsks(self.bash("rm -rf $UNSET_THING/data"), "could not be resolved")

    def test_rm_after_cd_out_of_project(self):
        self.assertAsks(self.bash("cd .. && rm -rf build"), "outside the project")

    def test_curl_post_to_payment_api(self):
        self.assertAsks(self.bash("curl -X POST https://api.stripe.com/v1/refunds -d charge=ch_1"), "payment API")
        self.assertAsks(self.bash("curl https://api.stripe.com/v1/payouts -u key: -d amount=100"), "POST")

    def test_custom_payment_host(self):
        self.config({"payment_hosts": ["api.mybank.example"]})
        self.assertAsks(self.bash("curl --request PUT https://api.mybank.example/transfers/1"), "payment API")

    def test_stripe_cli_write(self):
        self.assertAsks(self.bash("stripe refunds create --charge ch_123"), "Stripe")

    def test_shell_mail(self):
        self.assertAsks(self.bash("echo hi | mail -s test someone@example.com"), "sends email")

    def test_mcp_send_email(self):
        for tool in ("mcp__gmail__send_message", "mcp__resend__send-email", "mcp__outlook__sendMail",
                     "mcp__slack__slack_send_message", "mcp__gmail__reply"):
            with self.subTest(tool=tool):
                self.assertAsks(self.decide(tool, {"to": "a@example.com"}))

    def test_mcp_publish_pay_delete(self):
        for tool in ("mcp__cms__publish_post", "mcp__stripe__create_refund", "mcp__drive__delete_file",
                     "mcp__shop__create_payment", "mcp__gmail__trash_thread"):
            with self.subTest(tool=tool):
                self.assertAsks(self.decide(tool, {}))

    def test_config_ask_entry(self):
        self.config({"ask": ["Bash(terraform apply*)", "mcp__*__create_post"]})
        self.assertAsks(self.bash("terraform apply -auto-approve"), "ask list")
        self.assertAsks(self.decide("mcp__buffer__create_post", {"text": "hi"}), "ask list")

    def test_config_deny_entry(self):
        self.config({"deny": ["Bash(git push --force*)"]})
        decision, reason = self.bash("git push --force origin main")
        self.assertEqual(decision, "deny")
        self.assertIn("deny rule", reason)

    def test_protected_branches_from_config(self):
        self.config({"protected_branches": ["production"]})
        self.assertAsks(self.bash("git push origin production"), "production")
        self.assertSilent(self.bash("git push origin main"))


class Allowed(GateCase):
    """Everyday calls must pass through silently (no output, normal permission flow)."""

    def test_reads_and_builds(self):
        for cmd in ("ls -la", "git status", "npm test", "python3 -m pytest", "cat README.md | grep x"):
            with self.subTest(cmd=cmd):
                self.assertSilent(self.bash(cmd))

    def test_push_to_feature_branch(self):
        self.assertSilent(self.bash("git push -u origin feature/new-page"))

    def test_bare_push_on_feature_branch(self):
        self.git_repo("feature/x")
        self.assertSilent(self.bash("git push"))

    def test_rm_inside_project(self):
        self.assertSilent(self.bash("rm -rf build dist node_modules"))
        self.assertSilent(self.bash("rm -rf ./tmp/*"))
        self.assertSilent(self.bash("rm old.txt"))

    def test_text_mentions_are_not_commands(self):
        self.assertSilent(self.bash("echo 'remember to npm publish later'"))
        self.assertSilent(self.bash("grep -r 'git push origin main' docs/"))

    def test_npm_publish_dry_run(self):
        self.assertSilent(self.bash("npm publish --dry-run"))

    def test_curl_get_payment_api_and_post_elsewhere(self):
        self.assertSilent(self.bash("curl https://api.stripe.com/v1/charges -u key:"))
        self.assertSilent(self.bash("curl -X POST https://httpbin.org/post -d a=1"))

    def test_mcp_reads_and_drafts(self):
        for tool in ("mcp__gmail__search_threads", "mcp__gmail__create_draft", "mcp__drive__list_files",
                     "mcp__stripe__list_payments", "mcp__resend__get-email"):
            with self.subTest(tool=tool):
                self.assertSilent(self.decide(tool, {}))

    def test_other_tools_untouched(self):
        self.assertSilent(self.decide("Read", {"file_path": str(self.project / "x")}))
        self.assertSilent(self.decide("Write", {"file_path": str(self.project / "x"), "content": "y"}))

    def test_allow_entry_waives_gate(self):
        self.config({"allow": ["Bash(git push origin main)", "mcp__gmail__send_message"]})
        self.assertSilent(self.bash("git push origin main"))
        self.assertSilent(self.decide("mcp__gmail__send_message", {}))
        # The waiver is specific: other gated calls still ask.
        self.assertAsks(self.bash("npm publish"))

    def test_allow_waives_only_its_own_segment(self):
        self.config({"allow": ["Bash(git push origin main)"]})
        self.assertAsks(self.bash("git push origin main && npm publish"), "publishes")

    def test_deny_beats_allow(self):
        self.config({"allow": ["Bash(npm publish*)"], "deny": ["Bash(npm publish*)"]})
        self.assertEqual(self.bash("npm publish")[0], "deny")


class Malformed(GateCase):
    """Bad input never crashes the hook and never silently allows a risky call."""

    def test_empty_stdin_asks(self):
        code, out, _ = self.run_raw("")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_not_json_asks(self):
        code, out, _ = self.run_raw("this is not json {")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_json_without_tool_name_asks(self):
        code, out, _ = self.run_raw(json.dumps({"tool_input": {"command": "ls"}}))
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_json_array_asks(self):
        code, out, _ = self.run_raw("[1, 2, 3]")
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_bash_without_command_asks(self):
        self.assertAsks(self.decide("Bash", {"description": "no command"}), "no readable command")

    def test_tool_input_not_object(self):
        code, out, err = self.run_raw(json.dumps({"tool_name": "Bash", "tool_input": "rm -rf /"}))
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_unbalanced_quotes_still_checked(self):
        self.assertAsks(self.bash("git push origin main 'oops"))

    def test_broken_config_falls_back_to_builtins(self):
        self.config("{ not valid json")
        decision, reason = self.bash("npm publish")
        self.assertEqual(decision, "ask")
        self.assertIn("built-in rules only", reason)
        self.assertSilent(self.bash("ls"))

    def test_config_with_wrong_types_is_ignored(self):
        self.config({"allow": "everything", "deny": [1, 2], "ask": None})
        self.assertAsks(self.bash("npm publish"))
        self.assertSilent(self.bash("ls"))

    def test_config_not_an_object(self):
        self.config("[\"allow\"]")
        self.assertAsks(self.bash("npm publish"), "built-in rules only")

    def test_output_is_valid_hook_json(self):
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "npm publish"}})
        _, out, _ = self.run_raw(payload)
        data = json.loads(out)
        self.assertEqual(set(data), {"hookSpecificOutput"})
        self.assertEqual(set(data["hookSpecificOutput"]),
                         {"hookEventName", "permissionDecision", "permissionDecisionReason"})


if __name__ == "__main__":
    unittest.main()
