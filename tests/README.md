# operator-starter tests

Unit tests for the approval-gate hook, `scripts/approval_gate.py`. Python `unittest` only.

| Class | Covers |
| --- | --- |
| `Blocked` | Calls that must come back as "ask" (or "deny" from config): pushes to protected branches, force pushes, package publishing, `rm -rf` outside the project, payment API writes, shell mail, MCP send/publish/pay/delete tools, and `ask`/`deny` config entries. |
| `Allowed` | Everyday calls that must pass silently: reads, builds, feature-branch pushes, `rm` inside the project, text that only mentions a risky command, read and draft MCP tools, and `allow` entries. |
| `Malformed` | Empty, non-JSON or wrongly shaped input, and broken config files. The hook never crashes and never silently allows. |

## Run

From the repository root:

```bash
python3 -m unittest discover -s plugins/operator-starter/tests -v
```

The tests run the script as Claude Code does, with JSON on stdin, and need `git` on PATH.
