---
name: setup-operator
description: Sets up a project folder so Claude Code can help run a small business or side project safely. Interviews the person one question at a time (what they run, which tools they use, what must never happen without their approval, British or US spelling), then writes a CLAUDE.md with always-on working rules and approval rules, a memory folder (decisions, people, playbooks) with a README, an approval-gate config, and a Friday weekly-review routine. Use when someone says "set me up", "set up this project for my business", "make Claude work like an operator", "onboard me", "set up my workspace", "I run a small business, where do I start with Claude Code", or wants Claude to stop sending, paying or deleting without asking.
---

# Set up an operator workspace

A capable agent with access to your email, payments and code is useful on day one and
dangerous by day three, unless three things are written down: how it should work, what it
must never do without asking, and where it keeps what it learns. This skill writes those
three things into the project, from a short interview, in about ten minutes.

It writes files. It never sends, publishes, pays or deletes anything.

## The interview

Ask these **one at a time**. Wait for each answer, reflect it back in one line, then ask
the next. Never send them as a list.

1. **"What do you run, in a sentence or two? Who pays you, and roughly how many people
   are involved?"** You need the business in one line for the top of CLAUDE.md.
2. **"Which tools does the business run on?"** Prompt if stuck: email, calendar,
   payments, accounting, CRM, website or code host, social accounts, chat. Note which are
   connected to Claude (MCP servers or connectors) and which are not.
3. **"What must never happen without your say-so?"** Prompt with the usual four: sending
   anything to a customer or supplier, publishing anything public, moving or refunding
   money, deleting anything. Then ask for anything specific to them (a client list, a
   price change, a domain setting).
4. **"British or US spelling?"** Skip it if their answers already make it obvious, and
   say which you assumed.

If the person has already answered some of these in their message or in an existing
CLAUDE.md, do not ask again: confirm what you read in one line and ask only what is
missing. If they say "just use sensible defaults", use the defaults in
[references/claude-md-template.md](references/claude-md-template.md) and list what you
assumed at the end.

## What to write

Read the project first: an existing `CLAUDE.md`, `.claude/` folder or `memory/` folder
changes what you do. Then write:

1. **`CLAUDE.md`** at the project root, from
   [references/claude-md-template.md](references/claude-md-template.md). Keep it under 80
   lines: every line loads on every turn. Fill in the business, the tools and their
   answers to question 3 as concrete approval rules ("Ask before any `mcp__gmail__send*`
   or reply to a customer", not "be careful with email"). If a CLAUDE.md already exists,
   **merge**: keep every existing line, add the new sections under one
   `## Operator rules` heading, and if an existing rule contradicts a new one, keep the
   existing one and point it out.
2. **`memory/`** with `decisions/`, `people/` and `playbooks/`, and a `memory/README.md`
   from [references/memory-readme.md](references/memory-readme.md). Put a `.gitkeep` in
   each empty folder. If the person mentioned a decision already made in the interview
   (for example "we never discount"), write it as the first file in `decisions/`.
3. **`.claude/approval-gate.json`**, the config for the approval-gate hook this plugin
   ships. Turn each answer to question 3 that names a tool or command into an `ask`
   entry, and add any branch names they protect. Format and examples:
   [references/approval-gate.md](references/approval-gate.md). Only write entries you can
   tie to something they said; the built-in rules already cover the common cases.
4. **The weekly routine**: the CLAUDE.md template has a `## Weekly review` section that
   tells Claude to run the `weekly-review` skill on Fridays, or whenever the person says
   "weekly review". If they would rather a different day, use it.

Do not create anything else: no extra folders, no sample data, no rules they did not ask
for. A workspace with ten unused folders is worse than three that get used.

## Hand-over

Finish with a short summary, in this shape:

```text
Written:   CLAUDE.md (new / merged), memory/ (3 folders + README), .claude/approval-gate.json
Approval:  <their never-without-asking list, one line each, as now enforced>
Assumed:   <anything you defaulted, or "nothing">
Try it:    Ask me to "send a test email" or "push to main" and the gate will ask first.
Friday:    Say "weekly review".
```

Then say once, plainly, what protects them:

- **Installed as a plugin**: the approval-gate hook checks every shell command and every
  MCP tool call before it runs, and asks when it sends, publishes, pays or deletes. The
  CLAUDE.md rules are the second layer.
- **Uploaded as a skill only** (claude.ai or the desktop app): there is no hook. The
  CLAUDE.md rules are guidance Claude follows, not a lock. Say so; do not imply otherwise.

## What it never does

- Ask all the questions at once.
- Overwrite an existing CLAUDE.md or delete anything already in the project.
- Write a rule that weakens a protection the person already has (an allow entry they did
  not ask for, or removing an existing "ask" rule).
- Claim the gate makes anything impossible. It is a guard rail that asks first; it is not
  a sandbox, and a determined command can get round any text-matching hook.

## Example

> **Person:** Set me up. I make and sell candles online, just me and a part-timer.
>
> **Claude:** A one-person online candle shop with a part-time helper. Which tools does
> the business run on: shop platform, email, payments, accounting, socials?
>
> *(Answers: Shopify, Gmail, Stripe, Xero, Instagram via Buffer; Gmail and Buffer
> connected. Never without asking: emailing customers, posting to Instagram, refunds,
> changing prices. British spelling.)*
>
> Writes CLAUDE.md with rules such as "Ask before any send or reply in Gmail", "Ask before
> any Buffer post is created or scheduled", "Never issue a refund; draft it and ask";
> `.claude/approval-gate.json` with `"ask": ["mcp__buffer__create_post", "mcp__*__update_price*"]`;
> `memory/decisions/2026-10-16-prices-change-only-with-approval.md`; then the hand-over
> block above.

## Configuration

Two things vary: **which tools are connected** (they decide which MCP tool names go in
the gate config) and **where the project lives** (the files go in the folder Claude Code
was started in; start it in the folder you want set up).
