# Monitoring a host

**An alarm that runs on the Mac dies with the Mac.** The first alarm must live somewhere else
and fire when the host *stops talking*, not when it reports a problem.

## What to watch

| Signal | Alarm when | How | Lives |
| --- | --- | --- | --- |
| Host alive | no heartbeat for 15 minutes | a 5-minute LaunchAgent pings a dead-man URL | off-box |
| Each job ran | a job's ping is late or reports failure | the job wrapper pings per job | off-box |
| Claude signed in | the preflight call fails | wrapper preflight, then a failing ping | off-box |
| Memory | pressure critical, or swap nearly full | the heartbeat fails its ping | off-box |
| Disk | under 15% free | the heartbeat fails its ping | off-box |
| Job outcomes | not `ok` two runs in a row | read the outcome log daily | a ticket or message |
| The whole host | the heartbeat check itself goes quiet | a cloud scheduled task that reads the dead-man service | your chat or email |

A dead-man service (healthchecks.io is one; many exist, some self-hostable) gives each check a
URL. Ping it on success, ping its failure URL on failure, and it alerts when pings stop or
fail. Route alerts somewhere you actually read, and only for things a person must act on.

## The host heartbeat

One small job every 5 minutes. It pings success only when all of these hold, and the failure
URL with a one-line reason otherwise:

```bash
sysctl -n kern.memorystatus_vm_pressure_level    # 1 normal, 2 warning, 4 critical
sysctl -n vm.swapusage                           # total, used, free
df -kP /System/Volumes/Data | awk 'NR==2 {print 100-$5}'   # percent free
```

Append each reading to a local log too. A few weeks of that log answers "how much memory does
the next machine need" with evidence rather than a guess.

## Outcomes, not exit codes

The failure these hosts actually have: a job exits 0 while every model call inside it failed.
Nothing alerts, because nothing failed. So every job records an outcome
([claude-on-a-host.md](claude-on-a-host.md)) and something reads the outcomes. Rule of thumb:
two non-`ok` runs in a row raise a ticket automatically, with the log attached.
