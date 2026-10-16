# Scheduling with launchd

## Contents

- LaunchAgents, not cron
- A minimal agent
- Load and inspect
- The PATH trap
- The job wrapper
- Generating the agents
- Check


## LaunchAgents, not cron

On macOS, schedule jobs as **LaunchAgents** in `~/Library/LaunchAgents/`:

- They run in your login session, so they can use your keychain sign-ins.
- A `StartCalendarInterval` job whose time passed **while the Mac was asleep** runs once when
  it wakes. cron skips it.
- cron needs Full Disk Access for anything in protected folders; LaunchAgents run with your
  own permissions.

Neither replays runs missed while the Mac was **off**. Jobs that must not miss a day should
check "when did I last succeed?" on start rather than trust the calendar.

## A minimal agent

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.example.nightly-report</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/you/jobs/run-job.sh</string>
    <string>nightly-report</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>6</integer><key>Minute</key><integer>10</integer></dict>
  <key>StandardOutPath</key><string>/Users/you/jobs/logs/nightly-report.out</string>
  <key>StandardErrorPath</key><string>/Users/you/jobs/logs/nightly-report.err</string>
</dict>
</plist>
```

Use absolute paths everywhere; `~` is not expanded in a plist. Validate with `plutil -lint`.

## Load and inspect

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.example.nightly-report.plist  # load
launchctl bootout   gui/$(id -u)/com.example.nightly-report                               # unload
launchctl print     gui/$(id -u)/com.example.nightly-report                               # state, last exit
launchctl kickstart -k gui/$(id -u)/com.example.nightly-report                            # run now
launchctl list | grep com.example                                                          # PID, last exit, label
```

After editing a plist, `bootout` then `bootstrap`; launchd does not re-read it on its own.

## The PATH trap

launchd starts every job with `PATH=/usr/bin:/bin:/usr/sbin:/sbin`. Your shell profile is never
read. So a job that calls `claude` (usually installed in `~/.local/bin`), anything from
Homebrew (`/opt/homebrew/bin` on Apple silicon) or a Node, Python or Ruby from a version
manager **cannot find it**, or finds macOS's old system copy instead.

The worst version is silent: the job catches the failure, logs it and exits 0. Days of
"successful" runs that did nothing.

Fix it in one place: either set `PATH` in each plist's `EnvironmentVariables`, or start every
job through one wrapper that exports it. Whichever you choose, **anything else that runs your
checks must use the same rule.** A git hook that runs tests inherits the PATH of whatever made
the commit, so a job that commits gets its hooks run under the job's PATH. Put the PATH in one
sourced file and have the wrapper and the hooks both source it.

## The job wrapper

Every job goes through one script that:

1. Sets `PATH`, `HOME` and `USER` (launchd may not set `USER`, and some tools need it).
2. Sets a UTF-8 locale if none is set.
3. Takes a lock, so a slow run is not overlapped by the next one.
4. Injects secrets from a secrets manager or the keychain at run time, never from the plist.
5. Applies a timeout.
6. Records an **outcome**, not only the exit code, and pings the dead-man check
   ([monitoring.md](monitoring.md)).
7. Writes stdout and stderr to a log the job owns.

```bash
#!/bin/bash
# run-job.sh <job-name> - start every scheduled job through this
set -u
JOB="$1"; DIR="$HOME/jobs"; LOG="$DIR/logs/$JOB.log"
source "$DIR/env.sh"                     # PATH and locale, shared with git hooks
mkdir -p "$DIR/logs" "$DIR/locks" "$DIR/outcomes"
exec 9>"$DIR/locks/$JOB.lock"
if ! flock -n 9 2>/dev/null && ! shlock -f "$DIR/locks/$JOB.pid" -p $$ 2>/dev/null; then
  echo "$(date -u +%FT%TZ) outcome=skipped_locked" >> "$DIR/outcomes/$JOB"; exit 0
fi
START=$(date +%s); RUN=$(mktemp)
"$DIR/jobs/$JOB.sh" > "$RUN" 2>&1
CODE=$?
cat "$RUN" >> "$LOG"
OUTCOME=$(grep -o 'outcome=[a-z_]*' "$RUN" | tail -1 | cut -d= -f2); rm -f "$RUN"
[ -z "$OUTCOME" ] && OUTCOME=$([ $CODE -eq 0 ] && echo unknown || echo failed)
echo "$(date -u +%FT%TZ) outcome=$OUTCOME exit=$CODE secs=$(( $(date +%s) - START ))" >> "$DIR/outcomes/$JOB"
[ -n "${PING_URL:-}" ] && curl -fsS -m 10 "$PING_URL$([ "$OUTCOME" = ok ] || echo /fail)" >/dev/null || true
exit $CODE
```

macOS ships `shlock` but not `flock`; the line above uses whichever exists. Each job script
prints `outcome=ok` (or `no_work`, `model_calls_failed`, ...) as its last word, so the wrapper
records what happened rather than that a process ended. `unknown` is itself worth alerting on.

## Generating the agents

Keep the schedule in one register (a file listing job, schedule, command) and **generate** the
plists from it, with a check mode that compares what is loaded against the register. Hand-edited
plists drift, and a job that was never loaded looks exactly like a job that never fails.

## Check

`launchctl print gui/$(id -u)/<label>` shows `last exit code = 0` **and** the job's outcome log
shows `outcome=ok` for the last run. Both, not one.
