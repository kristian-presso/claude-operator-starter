# Updates and security

## Updates on your schedule

An automatic macOS install restarts the host overnight. With FileVault on, it then waits at the
unlock screen and runs nothing until someone unlocks it
([login-session-and-restarts.md](login-session-and-restarts.md)).

| Setting | Value | Where |
| --- | --- | --- |
| Install macOS updates | **off** | System Settings, General, Software Update, Automatic Updates |
| Security Responses and system files | **on** | same place; these install without a full OS upgrade |
| Download new updates when available | on | so patching is quick when you do it |

From a terminal (a person runs it, it needs `sudo`):

```bash
sudo defaults write /Library/Preferences/com.apple.SoftwareUpdate AutomaticallyInstallMacOSUpdates -bool false
defaults read /Library/Preferences/com.apple.SoftwareUpdate CriticalUpdateInstall   # expect 1
```

Then **patch by hand** when you are at the Mac, and always before leaving it alone for a long
time. Re-run the health check after any update.

## Least privilege

- **A standard user for the agents** on a dedicated host, separate from your admin account. On a
  laptop you also use day to day, running as yourself is an accepted trade-off; fix it on the
  next machine.
- **Narrow permissions** for scheduled agents: a tool allowlist, the sandbox where it fits, no
  blanket "allow everything".
- **Per-repo access tokens** with the smallest scope that works.

## Secrets

- Keep every key in a secrets manager or the keychain and inject it at run time
  (`security find-generic-password -w -s <name>` reads a keychain item in a script).
- Never in a plist, a script, a log, a commit or a chat.
- If a secrets manager CLI is used, sign it in once on the host and make the health check fail
  when it is installed but signed out.
