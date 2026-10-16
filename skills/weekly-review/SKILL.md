---
name: weekly-review
description: Runs a short Friday review of the week for someone running a small business or side project - what shipped, what is stuck and the one move that unsticks each item, decisions made (and writes them down), and the one thing to automate next. Gathers evidence from git history, project notes and connected tools before asking anything, asks at most two questions, and saves the review as a dated file. Use when someone says "weekly review", "Friday review", "how did the week go", "wrap up the week", "what did we ship this week", "end of week check-in", or on a Friday routine set up by setup-operator.
---

# Weekly review

A weekly review is worth ten minutes only if it changes next week. Most turn into a list
of what happened. This one ends with decisions written down, every stuck item given an
owner and a next move, and one automation picked.

It reads and writes notes. It never sends the review to anyone, and never builds the
automation it picks.

## 1. Gather before asking

Look first; ask only for what you cannot find. Use whatever is there:

- **Git**: `git log --since="7 days ago" --oneline --no-merges` (and on other branches with
  `--all`), merged pull requests if a code host is connected.
- **Project notes**: `memory/` (decisions, playbooks, last week's review in
  `memory/reviews/`), any to-do, notes or task file, recently changed files.
- **Connected tools**, read-only: the task tracker, calendar for meetings held, the inbox
  for threads waiting on a reply. Only if connected; do not ask the person to connect
  anything for this.
- **Last week's review**: if one exists, check its stuck items and its automation pick.
  Each is now done, still stuck, or dropped. Say which.

If you find nothing at all (a fresh folder, no git, nothing connected), say so in one line
and ask the person for the week in their own words: "What got done this week, and what
didn't?"

## 2. Ask at most two questions

After gathering, ask one question at a time, only if the answer is not already in what you
found:

1. "Anything that happened this week that isn't in the notes, such as a sale, a call or a
   problem?"
2. "What did you do by hand three or more times this week?" (feeds section 6)

If the person says "just write it", skip the questions and mark the gaps as gaps.

## 3. Write the review

Use this shape. Every line is something that happened or a decision, with its source.
No padding, no "great week".

```markdown
# Week ending YYYY-MM-DD

## Shipped
- What was finished and is now live or in use. Source (commit, PR, file, tool).

## Stuck
| Item | Stuck since | Why | Next move | Owner |
| --- | --- | --- | --- | --- |
| One line | date | the real blocker | one concrete action | a name |

## Decisions
- YYYY-MM-DD: decision in one sentence. Written to memory/decisions/<file>.md

## Last week's carry-over
- Item from last review: done / still stuck / dropped.

## Next automation
Next automation: what, in one line
Why this one:    frequency and cost of missing it, from this week's evidence
How to build it: scheduled script / reusable skill or saved prompt / existing tool feature

## Next week's one thing
The single outcome that would make next week a good week.
```

Rules for each section:

- **Shipped** means finished and in use. "Worked on" belongs in Stuck or nowhere.
- **Stuck**: anything open more than a week, waiting on someone, or failing. Every row
  gets a next move that is one action and an owner who is a named person, never left blank. Hand it
  back as a solution: if you can see the fix, say it.
- **Decisions**: anything decided this week that should outlast the conversation. Write
  each one to `memory/decisions/YYYY-MM-DD-short-title.md` (Decision, Why, Revisit), if
  that folder exists or the person agrees to create it. Do not invent decisions; a choice
  the person did not make is not a decision.
- **Next automation**: one pick, not a list. Prefer what was done by hand most often this
  week with the same steps each time. If the evidence is thin, or the person wants to
  think it through, hand off: "Run level-up for a proper pick" (the `level-up` skill in
  the operator-discipline plugin asks five questions and commits to one). Never build it
  here.

## 4. Save and hand over

Save to `memory/reviews/YYYY-MM-DD.md` (the Friday's date), creating the folder if
`memory/` exists; otherwise ask once where to keep it. Then show the review and end with
one line: the stuck item that most needs the person, as a yes/no question.

## What it never does

- Send, post or share the review anywhere. If they want it sent, draft the message and
  ask.
- Report activity as progress. Commits are evidence, not outcomes.
- List several automations, or start building one.
- Ask more than two questions, or ask about something the notes already answer.

## Example

> **Person:** weekly review
>
> *(Claude reads git log: 9 commits, "add gift-card checkout", "fix VAT on invoices".
> Reads memory/reviews/ from last Friday: stuck item "courier API key". Reads
> memory/decisions/: one new file from Tuesday.)*
>
> **Claude:** Anything this week that isn't in the commits or notes?
>
> **Person:** Two wholesale enquiries came in, I answered both by hand. Same email.
>
> Writes the review: Shipped (gift-card checkout, VAT fix); Stuck (courier API key, stuck
> since 2 Oct, waiting on the courier's support, next move: chase by phone Monday,
> owner: the founder); Decisions (Tuesday's "no free shipping under 30"); Next automation
> (a saved reply and enquiry form for wholesale leads, two this week, same answer each
> time). Saves to `memory/reviews/2026-10-16.md`, then asks: "Courier key: shall I draft
> the chaser for you to send Monday?"

## Configuration

Two things vary: **where reviews are saved** (default `memory/reviews/`) and **which
tools count as evidence** (whatever is connected; git alone is enough).
