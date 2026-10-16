# The login session, and what happens after a restart

## What has to stay running

| Must stay up | Why |
| --- | --- |
| A user **logged in** at the Mac | LaunchAgents live in that user's session (`gui/<uid>`). Log out and every job stops. |
| The **Claude desktop app**, if you reach the host through it | it is the bridge to this computer's files and shell; add it to Login Items |
| **Power** and **network** | see [power-and-sleep.md](power-and-sleep.md) |

**A terminal does not need to stay open.** launchd starts scheduled jobs inside the login
session, not inside a terminal window. Closing Terminal changes nothing. The exception is
anything you deliberately run in the foreground, such as a session kept alive in `tmux`, which
needs its own keep-alive.

The screen can lock and the display can sleep. Neither stops LaunchAgents.

(A LaunchDaemon in `/Library/LaunchDaemons` runs without anyone logged in, but as root or a
named user without that user's keychain or GUI session. For agent jobs that need a keychain
sign-in or the desktop app, stay with LaunchAgents and a logged-in user.)

## FileVault against automatic login

You cannot have both:

- **FileVault on** (recommended): the disk is encrypted, and after any restart the Mac waits at
  the unlock screen. **Nothing runs until someone unlocks it.**
- **FileVault off** with automatic login: the Mac comes back by itself after a restart, and
  anyone who takes it has the data.

From **macOS Tahoe 26.0**, FileVault can be unlocked over SSH after a restart if Remote Login
is enabled and a network connection is available (Apple's release notes, checked 16/10/2026;
`man apple_ssh_and_filevault` on the Mac). That removes most of the trade-off for a host. The
network has to come up before anyone logs in, which wired Ethernet does reliably and Wi-Fi may
not. Test it once, at home, before relying on it.

## The restart plan

Write it down before you need it:

1. **What restarts it.** Automatic macOS installs are the usual cause; turn them off
   ([updates-and-security.md](updates-and-security.md)). Power cuts are the other.
2. **Who unlocks it, and how.** At the Mac, or over SSH if your macOS and network allow it.
3. **How you will know it is waiting.** The off-box heartbeat goes quiet ([monitoring.md](monitoring.md)).
4. **What catches up.** LaunchAgents do not replay runs missed while the Mac was off
   ([scheduling-with-launchd.md](scheduling-with-launchd.md)).
