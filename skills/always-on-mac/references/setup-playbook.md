# Setup playbook

The build, in order. Each step ends with the health-check lines that prove it
([../scripts/host_check.sh](../scripts/host_check.sh)). Run the check at the start, to see where
you are, and at the end, to prove it.

Steps marked **(you)** need a person: a click in System Settings, a password, a sign-in or a
purchase. An agent can do the rest with a yes.

## Part 1 - the machine (about 20 minutes, at the Mac)

1. **(you) Finish Apple's setup** and sign in as the user that will run the jobs. On a dedicated
   machine, make that a standard user and keep a separate admin. Check: `session.user`.
2. **(you) FileVault on**, and write the restart plan now
   ([login-session-and-restarts.md](login-session-and-restarts.md)). Check: `security.filevault`.
3. **(you) Power.**
   ```bash
   sudo pmset -c sleep 0
   sudo pmset -c lowpowermode 0
   sudo pmset disablesleep 1          # laptop
   sudo pmset -a autorestart 1        # desktop
   ```
   Laptop: charge limit around 80%, lid open, plugged in. Desktop: on a UPS. Check: `power.*`.
4. **(you) Updates on your schedule.** Automatic macOS installs off, security responses on
   ([updates-and-security.md](updates-and-security.md)). Check: `updates.*`.
5. **(you) Remote access.** Install one private device network on the host and your phone,
   turn on Remote Login (only your user) and the firewall ([remote-access.md](remote-access.md)).
   Check: `remote.*`.

## Part 2 - the tools (about 20 minutes)

1. **Homebrew**, then the toolchain your jobs use (git, Node, Python, a secrets manager CLI if
   you use one).
2. **Claude Code**, then **(you)** sign it in. For a host left alone for weeks, also
   `claude setup-token` into the keychain or secrets manager
   ([claude-on-a-host.md](claude-on-a-host.md)). Check: `claude.cli`, `claude.auth`.
3. **(you) The Claude desktop app**, signed in and in Login Items, if you will reach the host
   through it. Check: `session.desktop-app`.

## Part 3 - the work (about 30 minutes)

1. **Clone the repos** into one workspace folder.
2. **One PATH file**, sourced by the job wrapper and by the git hooks
   ([scheduling-with-launchd.md](scheduling-with-launchd.md)).
3. **Generate and load the LaunchAgents** from the job register. Check: `jobs.*`.
4. **The hourly sync job** for each repo ([backups-and-sync.md](backups-and-sync.md)).

## Part 4 - knowing it works (about 20 minutes)

1. **(you, if it costs money) Time Machine** to an external disk, and an off-site snapshot of
   what git does not hold. Check: `backup.timemachine`.
2. **The off-box dead-man**: one check per job plus a 5-minute host heartbeat
   ([monitoring.md](monitoring.md)).
3. **Outcome alerts**: two non-`ok` runs raise a ticket.
4. **(you) A restart test.** Restart, unlock the way the plan says, and confirm the jobs resume
   and the heartbeat recovers. On a desktop, pull the plug once too.
5. **Run the health check again.** Zero `GAP` lines and every `MANUAL` line confirmed by a
   person is done.

## Keeping it right

Run the health check weekly (a scheduled job can) and after every macOS update. Every manual
fix goes into this playbook for the next machine.
