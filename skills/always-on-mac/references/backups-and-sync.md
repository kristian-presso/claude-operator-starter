# Backups and sync

Three layers, because each covers what the others do not:

| Layer | Holds | Restores |
| --- | --- | --- |
| **Git remote** (private, yours) | scripts, prompts, skills, config, anything in a repo | any file, any version, onto any machine |
| **Time Machine** (external disk) | the whole Mac, hourly | the whole Mac or one file, quickly |
| **Off-site snapshot** (encrypted, for example restic to object storage) | what git does not hold: LaunchAgents, local settings, state files | the host's own setup after a theft or fire |

## The host's disk is the working copy; the remote is the record

While it runs, the host is where work happens. That only stays safe if every change reaches the
remote quickly:

- **An hourly sync job** per repo on the host: pull (fast-forward or rebase), then push. Repos
  the host writes to commit their own changes first; repos it only reads just pull.
- **Never sync a checkout while a job is running from it.** Skip and retry next hour.
- **Know when a push failed.** If a pre-push hook refuses a commit, the commit is stranded on
  the host. Leave a marker both you and the agent see, and clear it automatically once the
  commit reaches the remote.

## Why pushes strand

A hook that runs on push (tests, a secret scan, linters) judges the commit in **the environment
that made it**. On a host that is often a scheduled job with launchd's bare PATH, so the hook
runs the wrong interpreter or cannot find a tool, and a good commit is refused.

- Give hooks the same PATH file as the jobs ([scheduling-with-launchd.md](scheduling-with-launchd.md)).
- When a push is refused, the marker should name the failing hook, so the fix is obvious.

## Time Machine

Needs an external disk or a network target that supports it. Check with
`tmutil destinationinfo`. `tmutil latestbackup` needs Full Disk Access for the terminal, so the
check may ask a person to look.

## Restore drill

Once a quarter, restore one file from each layer to a scratch folder and open it. An untested
backup is a hope.
