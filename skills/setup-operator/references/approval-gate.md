# Approval gate config

The operator-starter plugin ships a PreToolUse hook (`scripts/approval_gate.py`) that runs
before every shell command and every MCP tool call. It reads `.claude/approval-gate.json`
from the project, if there is one.

## What it asks about with no config at all

- `git push` to `main` or `master` (including a bare `git push` while on one), and any
  force push, mirror push or remote branch delete.
- Publishing a package or release: `npm`, `pnpm`, `yarn`, `bun` and `cargo publish`,
  `twine upload`, `gem push`, `gh release create`. A `--dry-run` passes.
- `rm -r` / `rm -rf` on anything outside the project, on the whole project, or on a
  path built from a variable it cannot resolve.
- `curl`, `wget` or `httpie` sending POST, PUT, PATCH or DELETE to a known payment API
  host (Stripe, PayPal, Square, GoCardless, Paddle, Wise and others), and Stripe CLI
  commands that create, update, cancel or refund.
- Shell mail commands (`mail`, `sendmail`, `mutt`).
- MCP tools whose name says they send, reply, forward, publish, pay, charge, refund,
  transfer or delete, such as `mcp__gmail__send_message` or `mcp__drive__delete_file`.
  Tools whose name starts with a read verb (get, list, search, read, draft, compose and
  similar) pass.

It checks every part of a compound command (`a && b; c | d`), command substitutions and
`bash -c "..."`.

## The config file

All keys are optional.

```json
{
  "allow": ["Bash(git push origin main)"],
  "ask": ["mcp__buffer__create_post", "mcp__*__update_price*", "Bash(terraform apply*)"],
  "deny": ["Bash(git push --force*)"],
  "protected_branches": ["main", "production"],
  "payment_hosts": ["api.mybank.example"]
}
```

| Key | Effect |
| --- | --- |
| `ask` | Extra calls to stop and ask about. |
| `deny` | Calls to refuse outright. Claude is told not to retry. |
| `allow` | Waives the gate for that exact call. It never grants a permission Claude Code would otherwise ask for. |
| `protected_branches` | Replaces the default `main`, `master`. |
| `payment_hosts` | Added to the built-in payment API list. |

Entries use the same shape as Claude Code permission rules: `ToolName` or
`ToolName(pattern)`, with `*` wildcards. For `Bash` the pattern matches the whole command
or any one part of a compound command. For other tools it matches the tool input as
compact JSON, for example `mcp__gmail__send_message(*"to":"*@mycompany.com"*)`.

Precedence: `deny`, then `allow`, then `ask`. A broken file (bad JSON, wrong types) is
ignored with a note in the reason, and the built-in rules still apply.

## Turning interview answers into entries

| They said | Entry |
| --- | --- |
| "Never post to social without asking" (Buffer connected) | `"ask": ["mcp__buffer__create_post", "mcp__buffer__edit_post"]` |
| "Never change prices" (shop connected as `shop`) | `"ask": ["mcp__shop__*price*"]` |
| "Do not touch the production branch" | `"protected_branches": ["main", "production"]` |
| "Never run terraform apply" | `"deny": ["Bash(terraform apply*)"]` |
| "Pushing to main is fine, I am the only one here" | `"allow": ["Bash(git push origin main)"]`, and confirm they mean it |

MCP tool names follow `mcp__<server>__<tool>`. If you do not know a connected tool's
exact name, use a wildcard on the part you know (`mcp__*__create_post`) rather than
guessing.

## Limits

This is a guard rail, not a lock. It matches text, so an obfuscated command can get past
it, and it does not run at all when the skill is used without the plugin (for example on
claude.ai). For hard limits, use Claude Code's own permission rules (`permissions.ask` and
`permissions.deny` in `.claude/settings.json`) as well, and keep credentials scoped to
what the work needs.
