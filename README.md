# Operator starter for Claude Code

**Set up a project so Claude Code can help run a small business or side project safely: one interview writes the rules, a hook makes Claude ask before it sends, publishes, pays or deletes, and a Friday review keeps the week honest.**

```bash
/plugin marketplace add kristian-presso/claude-operator-starter
/plugin install operator-starter@claude-operator-starter
```

One department of [claude-skills](https://github.com/kristian-presso/claude-skills), where all departments live in one place. Free, MIT licensed, no sign-up.

The other departments are skills: judgement Claude picks up when a task calls for it. This one is the wiring. A capable agent with access to your email, payments and code is useful on day one and dangerous by day three, unless three things are written down: how it should work, what it must never do without asking, and where it keeps what it learns. This plugin writes those into your project, then puts a gate in front of the actions you cannot take back.

## What is in it

| Part | Use it when |
| --- | --- |
| [setup-operator](skills/setup-operator/SKILL.md) (skill) | Starting out in a project folder. Asks four questions one at a time (what you run, which tools you use, what must never happen without your say-so, British or US spelling), then writes a `CLAUDE.md` with working rules and approval rules, a `memory/` folder (`decisions/`, `people/`, `playbooks/`) with a README, a `.claude/approval-gate.json`, and the Friday routine. Merges into an existing `CLAUDE.md` rather than replacing it. Say "set me up". |
| [weekly-review](skills/weekly-review/SKILL.md) (skill) | Fridays. Reads the week's git history, notes and last week's review before asking anything, then writes what shipped, what is stuck (each with a next move and an owner), decisions made (saved to `memory/decisions/`), and the one thing to automate next. Saves to `memory/reviews/`. Say "weekly review". |
| Approval gate (hook) | Always, once installed. A `PreToolUse` hook that runs before every shell command and MCP tool call and makes Claude Code ask you first when the call sends, publishes, pays or deletes. |

## Tested, not just written

Each skill is evaluated with Claude Code's built-in `claude plugin eval`: five cases per skill (three it should handle, two near-misses it must leave alone), each run three times with the plugin and three times without, graded by a separate model. A skill ships only if Claude does better with it than without it. Results from 16/10/2026:

| Skill | Score with | Without | Gain |
| --- | --- | --- | --- |
| setup-operator | 1.00 | 0.83 | +0.17 |
| weekly-review | 1.00 | 0.78 | +0.22 |

Both near-miss cases for each skill scored 1.00: the skills stayed out of the way. The hook has 45 unit tests of its own (see below).

## Install

### Claude Code

On its own, from this repository:

```bash
/plugin marketplace add kristian-presso/claude-operator-starter
/plugin install operator-starter@claude-operator-starter
```

Or with every other department, from the hub:

```bash
/plugin marketplace add kristian-presso/claude-skills
/plugin install operator-starter@claude-skills
```

Use one or the other, not both, or the hook runs twice.

The hook needs `python3` on your PATH (macOS and Linux have it; on Windows use WSL or install Python). Run `/hooks` in Claude Code to see it listed under `PreToolUse`.

### Claude app

On claude.ai or the Claude desktop app, download this repository as a zip (Code, then Download ZIP), take `skills/setup-operator/` or `skills/weekly-review/` (the folder containing `SKILL.md`), zip that folder on its own and upload it in your skills settings. Each skill works on its own. The hook does not come with them: in the app, the `CLAUDE.md` rules are guidance, not a lock.

## How the approval gate works

Claude Code runs `scripts/approval_gate.py` before every `Bash` call and every `mcp__*` tool call, passing the call as JSON on stdin. The script answers in one of three ways: say nothing (the call goes ahead as normal), `ask` (Claude Code stops and shows you the call with the reason, and you approve or refuse), or `deny` (the call is refused and Claude is told not to retry). Standard-library Python, no dependencies, and it never crashes into a silent allow: malformed input or a broken config falls back to the built-in rules.

With no configuration it asks before:

- `git push` to `main` or `master` (including a bare `git push` while on one), and any force push, mirror push or remote branch delete
- `npm`, `pnpm`, `yarn`, `bun` or `cargo publish`, `twine upload`, `gem push`, `gh release create` (a `--dry-run` passes)
- `rm -rf` on anything outside the project, on the project itself, or on a path built from a variable it cannot resolve
- `curl`, `wget` or `httpie` POST, PUT, PATCH or DELETE to a payment API (Stripe, PayPal, Square, GoCardless, Paddle, Wise and others), and Stripe CLI writes
- shell `mail`, `sendmail` and `mutt`
- MCP tools named for sending, replying, forwarding, publishing, paying, refunding, transferring or deleting, such as `mcp__gmail__send_message`; read and draft tools pass

It checks every part of a compound command (`a && b; c | d`), `$(...)` substitutions and `bash -c "..."`.

### Configure it

`setup-operator` writes `.claude/approval-gate.json` from your interview answers. You can also edit it by hand. All keys are optional:

```json
{
  "ask":   ["mcp__buffer__create_post", "Bash(terraform apply*)"],
  "deny":  ["Bash(git push --force*)"],
  "allow": ["Bash(git push origin main)"],
  "protected_branches": ["main", "production"],
  "payment_hosts": ["api.mybank.example"]
}
```

| Key | Effect |
| --- | --- |
| `ask` | Extra calls to stop and ask about. |
| `deny` | Calls to refuse outright. |
| `allow` | Waives the gate for that exact call. It never grants a permission Claude Code would otherwise ask for. |
| `protected_branches` | Replaces the default `main`, `master`. |
| `payment_hosts` | Added to the built-in payment API list. |

Entries use the same shape as Claude Code permission rules, `ToolName` or `ToolName(pattern)` with `*` wildcards. Precedence is `deny`, then `allow`, then `ask`. The full format, with examples for turning interview answers into entries, is in [skills/setup-operator/references/approval-gate.md](skills/setup-operator/references/approval-gate.md).

Two honest limits. It is a guard rail that matches text, not a sandbox: an obfuscated command can get past it, so keep credentials scoped and use Claude Code's own `permissions.deny` rules for anything that must be impossible. And it only exists in Claude Code with the plugin installed.

## Works with

- [operator-discipline](https://github.com/kristian-presso/claude-operator-skills): the `CLAUDE.md` this writes includes short forms of `pushback` and `solutions-shape`, and the weekly review hands off to `level-up` when the automation pick needs more thought. Install it alongside for the full versions.
- [agent-builder](https://github.com/kristian-presso/claude-agent-builder): when the weekly review picks something to automate, `skill-builder` turns it into a skill.

## Configuration

Two things vary: which tools you have connected (they decide which MCP tool names belong in your gate config) and where you keep notes (default `memory/` in the project). Neither needs any particular service to work.

## Re-run the evals and tests

The eval cases live in `evals/`, one folder per skill. From the repository root:

```bash
claude plugin eval . --trust-plugin --scaffold --ablation with-without --runs 3 --no-publish
```

Every push runs the same checks as CI: each skill through the validator, the hook's unit tests (blocked, allowed and malformed input, standard library only, `git` on PATH), and the manifests through `claude plugin validate`:

```bash
for d in skills/*/; do python3 tools/validate_skill.py "$d"; done
python3 -m unittest discover -s tests -v
claude plugin validate .
```

## Feedback

Two minutes on [this form](https://tally.so/r/7XlJbL?source=operator-starter) tells me what worked, what broke and what to build next. Every answer gets read. Bugs with steps to reproduce are best as a GitHub issue: if the gate asked when it should not have, let something through it should have stopped, or a skill produced the wrong thing, tell me what you typed and what happened.

## More departments

This is one of six. [claude-skills](https://github.com/kristian-presso/claude-skills) has all departments in one place: operator discipline, the operator starter, building with Claude, go-to-market, marketing and UK business, installable together or one at a time.

## All of it in one install

These skills also run inside [Corey](https://getcorey.ai), alongside the rest of the library I use to run my business: one install that already knows your business, remembers it between chats and keeps itself up to date. It is free for individuals.

## Licence

[MIT](LICENSE). Take them, fork them, strip the parts you disagree with.

How these were built, and why, is written up at [kristianpapadakis.com/guides](https://kristianpapadakis.com/guides).
