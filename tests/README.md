# operator-starter tests

Unit tests for the approval-gate hook and the always-on-mac scripts. Python `unittest`, standard
library only.

## Approval gate: `test_approval_gate.py`

Covers `scripts/approval_gate.py`.

| Class | Covers |
| --- | --- |
| `Blocked` | Calls that must come back as "ask" (or "deny" from config): pushes to protected branches, force pushes, package publishing, `rm -rf` outside the project, payment API writes, shell mail, MCP send/publish/pay/delete tools, and `ask`/`deny` config entries. |
| `Allowed` | Everyday calls that must pass silently: reads, builds, feature-branch pushes, `rm` inside the project, text that only mentions a risky command, read and draft MCP tools, and `allow` entries. |
| `Malformed` | Empty, non-JSON or wrongly shaped input, and broken config files. The hook never crashes and never silently allows. |

## always-on-mac

| File | Covers |
| --- | --- |
| `test_host_check.py` | `skills/always-on-mac/scripts/host_check.sh`, run on any OS with stubbed `pmset`, `launchctl`, `fdesetup` and friends |
| `test_job_wrapper.py` | the job wrapper in `skills/always-on-mac/references/scheduling-with-launchd.md`, extracted from the markdown as a reader would copy it |

## Run

From the repository root:

```bash
python3 -m unittest discover -s tests -v
```

The approval-gate tests run the script as Claude Code does, with JSON on stdin, and need `git` on PATH.
