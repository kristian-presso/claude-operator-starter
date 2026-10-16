# Claude Code on a host

## Signing in for unattended use

Two ways, both read by `claude` when a job runs. Checked 16/10/2026 at
code.claude.com/docs/en/authentication:

| Method | How | Good for | Watch for |
| --- | --- | --- | --- |
| Keychain sign-in | run `claude`, sign in once (`/login`) | a host you sit at now and then | lives in the login keychain; a locked keychain in an SSH session makes Claude Code fall back to `~/.claude/.credentials.json`; check with `claude auth status` |
| Long-lived token | `claude setup-token`, then give jobs `CLAUDE_CODE_OAUTH_TOKEN` | a host left alone for weeks | lasts **one year**; needs a Pro, Max, Team or Enterprise plan; it can only make model requests (no claude.ai connectors, no Remote Control); put the expiry date in your calendar |

`claude setup-token` prints the token and does not save it. Store it in a secrets manager or the
keychain and inject it at run time. Never write it into a plist, a script, a log or a commit.

`--bare` mode does not read `CLAUDE_CODE_OAUTH_TOKEN`; a job that passes `--bare` needs
`ANTHROPIC_API_KEY` or an `apiKeyHelper` instead. If `ANTHROPIC_API_KEY` is set in the job's
environment it takes precedence over the token in non-interactive runs, which bills the API key
rather than the subscription: unset it unless that is what you want.

**Preflight.** Before a batch of jobs, make one cheap model call and alert if it fails.
Otherwise a sign-in failure shows up as every job "succeeding" with nothing done.

## Running a job

Non-interactive runs use print mode:

```bash
claude -p "Summarise yesterday's error log in logs/app.log and write it to reports/$(date +%F).md" \
  --allowedTools "Read,Write,Bash(git log:*)" --max-turns 20 --output-format json
```

Give the narrowest tool allowlist that lets the job finish. Avoid
`--dangerously-skip-permissions` on a machine that holds anything you care about; if a job
genuinely needs broad rights, run it as a separate standard user ([updates-and-security.md](updates-and-security.md)).
Check the current flags with `claude --help`; they change between releases.

## Finding the binary

`claude` usually installs to `~/.local/bin`, which launchd's PATH does not include. See
[scheduling-with-launchd.md](scheduling-with-launchd.md). This one gap takes down whole sets of
jobs for days.

## The desktop app as a bridge

If you reach the host from your phone or another machine through the Claude desktop app, the
app must be **running** on the host. Add it to Login Items (System Settings, General, Login
Items) so it returns after a restart. It does not need a window open.

## Outcomes, not exit codes

Make every job that calls a model record what happened, in a field a machine can read:

```text
outcome=ok | failed | model_calls_failed | skipped_locked | no_work
```

With `--output-format json`, the result object reports whether the run errored; turn that into
the outcome rather than trusting the process exit code alone. Alert when a job's outcome is not
`ok` (or `no_work`) two runs in a row ([monitoring.md](monitoring.md)).
