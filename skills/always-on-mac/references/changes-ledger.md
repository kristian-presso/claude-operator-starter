# Changes ledger

Facts in this skill that move. Re-check the source before quoting one.

| Fact | Checked | Value | Re-check at |
| --- | --- | --- | --- |
| `claude setup-token` | 16/10/2026 | one-year OAuth token, printed not saved, used via `CLAUDE_CODE_OAUTH_TOKEN`; needs Pro, Max, Team or Enterprise; model requests only; not read in `--bare` mode | code.claude.com/docs/en/authentication |
| Claude Code credential storage on macOS | 16/10/2026 | login keychain; if the keychain rejects the write (for example locked in SSH) it falls back to `~/.claude/.credentials.json` (mode 0600) | same page |
| FileVault unlock over SSH | 16/10/2026 | from macOS Tahoe 26.0, after a restart, if Remote Login is on and a network connection is available | support.apple.com/en-us/124963; `man apple_ssh_and_filevault` |
| Battery charge limit setting | 04/10/2026 | in System Settings, Battery from macOS 26.4 | support.apple.com/HT212049 |
| launchd default PATH | 04/10/2026 | `/usr/bin:/bin:/usr/sbin:/sbin` | `launchctl print gui/$(id -u)` on the host |
| macOS system Ruby | 04/10/2026 | 2.6 at `/usr/bin/ruby` | `/usr/bin/ruby -v` |
| Tailscale free Personal plan | 16/10/2026 | up to 6 users, unlimited user devices; personal, non-commercial use; public-domain sign-ins (Gmail, Apple, personal GitHub) are enrolled automatically, custom domains start a business trial | tailscale.com/pricing |
| NordVPN Meshnet | 04/10/2026 | free, no subscription needed; up to 60 devices (10 own, 50 linked); macOS 12+ | nordvpn.com/meshnet |
| Mesh VPNs as seen by a script | 04/10/2026 | each shows as a `utun` interface with a 100.64.0.0/10 address; check the interface rather than `scutil --nc list` | `ifconfig` on the host |
