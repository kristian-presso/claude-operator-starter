---
name: always-on-mac
description: Sets up and checks a Mac you own as an unattended host for scheduled agent work - Claude Code jobs on a timer, launchd LaunchAgents instead of cron, the bare PATH that silently breaks jobs, sleep and power settings, FileVault and restarts, signing Claude in for unattended runs, reaching the machine remotely, off-box monitoring and backups. Use when someone asks "run Claude Code on a schedule on my Mac", "my cron job can't find claude", "my launchd job exits 0 but did nothing", "keep my Mac awake for agents", "Mac mini as an always-on server", "how do I reach my Mac from my phone", "my jobs stopped after a restart", or "check my Mac is set up to run jobs unattended". Not for cloud-hosted schedules; if every job can run in a cloud scheduler, it says so.
---

# Always-on Mac

How to make a Mac run scheduled agent work around the clock, and how to know when it has
quietly stopped. Every rule here comes from the same failure: the machine looks fine, the jobs
exit 0, and nothing useful happens for days. So this skill leads with **checks**, not settings.

## Start here: does this need a Mac at all?

| Tier | Runs where | Good for | Stops when |
| --- | --- | --- | --- |
| The desktop app, by hand | your machine, while you use it | ad hoc work | you close the lid |
| Cloud scheduled tasks | a provider's cloud | work done through connectors: reading, writing, research, reports | rarely, but coarse schedules and no local files |
| An always-on Mac | a machine you own, 24/7 | real repos and files, local tools or models, frequent schedules | power, network, or a restart nobody unlocks |

Recommend the cloud tier first. A Mac earns its place when the work needs the real files, a
local tool or model, or runs every few minutes. Even then, keep one cloud task whose only job is
noticing the Mac has gone quiet.

## Route the question

| Question is about | Read |
| --- | --- |
| Building a host from scratch, in order, with the check for each step | [references/setup-playbook.md](references/setup-playbook.md) |
| Scheduling jobs, LaunchAgents vs cron, the PATH trap, the job wrapper, catch-up after sleep | [references/scheduling-with-launchd.md](references/scheduling-with-launchd.md) |
| Running Claude Code unattended: sign-in, tokens, permissions, outcomes | [references/claude-on-a-host.md](references/claude-on-a-host.md) |
| Sleep, Low Power Mode, battery charge limit, the lid, power cuts | [references/power-and-sleep.md](references/power-and-sleep.md) |
| What must stay running, FileVault against auto-login, the restart plan | [references/login-session-and-restarts.md](references/login-session-and-restarts.md) |
| Reaching the Mac from a phone or laptop, SSH, private networks, the firewall | [references/remote-access.md](references/remote-access.md) |
| Knowing it has stopped: dead-man checks, heartbeat, outcome alerts | [references/monitoring.md](references/monitoring.md) |
| Backups, syncing repos, pushes that strand | [references/backups-and-sync.md](references/backups-and-sync.md) |
| macOS updates, least privilege, secrets | [references/updates-and-security.md](references/updates-and-security.md) |
| Which Mac to buy, how much memory, moving to a new host | [references/choosing-and-migrating.md](references/choosing-and-migrating.md) |
| Any version, price or OS fact with a date | [references/changes-ledger.md](references/changes-ledger.md) |

## Health check

When asked to check a host, and you can run commands on it, run
[scripts/host_check.sh](scripts/host_check.sh). It only reads, needs no `sudo`, and prints one
line per check as `PASS`, `GAP` or `MANUAL` (a person must confirm, for example the battery
charge limit). If you cannot run commands, give the person the same checks to paste. Never
report a setting as done because it was set once; report what the check shows now.

## Rules

1. **Run the check, then believe it.** A setting you remember making is not a setting that is
   set. Check before and after any change.
2. **Outcome over exit code.** A job that exits 0 while every model call inside it failed is
   the most common failure on these hosts. Every job records an outcome.
3. **Alarms live off the box.** Anything that runs on the Mac dies with it.
4. **The person does the settings; the agent does the files.** Anything needing `sudo`, a
   click in System Settings, a password, a sign-in or a purchase is the person's. Say which is
   which, and give the exact command or menu path.
5. **Quote dated facts with their date** and where to re-check them.

## Example

> **User:** I scheduled a Claude Code job with launchd. It shows exit 0 every night but nothing happens.
>
> **Answer:** Almost certainly the PATH. launchd starts jobs with `/usr/bin:/bin:/usr/sbin:/sbin`, and `claude` usually lives in `~/.local/bin`, so the job cannot find it. If your script catches the failure and exits 0, launchd reports success.
>
> Check: `launchctl print gui/$(id -u)/<your.label> | grep -A3 environment`, and look at the job's own log for "command not found". Fix it in one place: a wrapper script that exports `PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"`, then runs the job and records an outcome (`ok` only if the model calls succeeded). Point the plist's `ProgramArguments` at the wrapper, reload with `launchctl bootout` then `bootstrap`, and add a dead-man ping so the next silent failure alerts you.

## Configuration

Two things vary: **laptop or desktop** (charge limit and lid rules apply only to laptops;
automatic restart after a power cut only to desktops) and **how you reach the machine**
(the Claude desktop app, a private device network, or both).
