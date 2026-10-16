# operator-starter

A way of working for running a small business or side project with Claude Code. One
interview sets up your project, a hook stops Claude before it sends, publishes, pays or
deletes, and a Friday review keeps the week honest.

The other plugins in this marketplace are skills: judgement Claude picks up when a task
calls for it. This one is the wiring. It writes the always-on rules into your `CLAUDE.md`,
gives Claude somewhere to keep what it learns, and puts a gate in front of the actions you
cannot take back.

## What is in it

| Part | What it does |
| --- | --- |
| **setup-operator** (skill) | Asks four questions one at a time: what you run, which tools you use, what must never happen without your say-so, British or US spelling. Then writes a `CLAUDE.md` with working rules and approval rules, a `memory/` folder (`decisions/`, `people/`, `playbooks/`) with a README, a `.claude/approval-gate.json`, and the Friday routine. Merges into an existing `CLAUDE.md` rather than replacing it. |
| **weekly-review** (skill) | Reads the week's git history, notes and last week's review before asking anything, then writes: what shipped, what is stuck (each with a next move and an owner), decisions made (written to `memory/decisions/`), and the one thing to automate next. Saves to `memory/reviews/`. Hands off to `level-up` when the automation pick needs more thought. |
| **Approval gate** (hook) | A `PreToolUse` hook that runs before every shell command and MCP tool call, and makes Claude Code ask you first when the call sends, publishes, pays or deletes. Standard-library Python, no dependencies. |

Say "set me up" in a new project folder to start. Say "weekly review" on Fridays.

## The approval gate

With no configuration it asks before:

- `git push` to `main` or `master`, and any force push or remote branch delete
- `npm`, `pnpm`, `yarn`, `bun` or `cargo publish`, `twine upload`, `gem push`, `gh release create`
- `rm -rf` on anything outside the project, or the project itself
- `curl` or `wget` POST, PUT, PATCH or DELETE to a payment API (Stripe, PayPal, Square, GoCardless and others), and Stripe CLI writes
- shell `mail` and `sendmail`
- MCP tools named for sending, replying, publishing, paying, refunding or deleting, such as `mcp__gmail__send_message`; read and draft tools pass

It checks every part of a compound command, `$(...)` and `bash -c "..."`. Add your own
rules in `.claude/approval-gate.json`:

```json
{
  "ask":   ["mcp__buffer__create_post", "Bash(terraform apply*)"],
  "deny":  ["Bash(git push --force*)"],
  "allow": ["Bash(git push origin main)"],
  "protected_branches": ["main", "production"]
}
```

`allow` only waives the gate; it never grants a permission Claude Code would otherwise ask
for. The full format is in
[skills/setup-operator/references/approval-gate.md](skills/setup-operator/references/approval-gate.md).

Two honest limits. It is a guard rail that matches text, not a sandbox: an obfuscated
command can get past it, so keep credentials scoped and use Claude Code's own
`permissions.deny` rules for anything that must be impossible. And it only exists in
Claude Code with the plugin installed: if you upload the skills to the Claude app, the
`CLAUDE.md` rules are guidance, not a lock.

## Works with

- **operator-discipline**: the `CLAUDE.md` this writes includes the short forms of
  `pushback` and `solutions-shape`, and the weekly review hands off to `level-up`. Install
  it alongside for the full versions.
- **agent-builder**: when the weekly review picks something to automate, `skill-builder`
  turns it into a skill.

## Install

In Claude Code:

```bash
/plugin marketplace add kristian-presso/claude-skills
/plugin install operator-starter@claude-skills
```

The hook needs `python3` on your PATH (macOS and Linux have it; on Windows use WSL or
install Python). Run `/hooks` in Claude Code to see it listed under `PreToolUse`.

On claude.ai or the Claude desktop app, upload `skills/setup-operator/` or
`skills/weekly-review/` as a custom skill. The hook does not come with them.

## Tests

The hook has unit tests covering blocked, allowed and malformed input, standard library
only:

```bash
python3 -m unittest discover -s plugins/operator-starter/tests -v
```

## Configuration

Two things vary: which tools you have connected (they decide which MCP tool names belong
in your gate config) and where you keep notes (default `memory/` in the project).

## Feedback

Used this? [Tell me what worked and what broke](https://tally.so/r/7XlJbL?source=operator-starter) - two minutes, every answer read.

## Licence

MIT.
