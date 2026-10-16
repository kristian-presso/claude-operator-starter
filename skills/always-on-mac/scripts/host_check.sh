#!/bin/bash
# host_check.sh - read-only health check for a Mac that runs scheduled agent jobs.
#
# Prints one line per check:  PASS|GAP|MANUAL  <id>  <what it found / what to do>
# Exit code: 0 if no GAP lines, 1 otherwise. Needs no sudo and changes nothing.
#
#   bash host_check.sh            run every check
#   bash host_check.sh --gaps     print only GAP and MANUAL lines
#
# Works with the bash 3.2 that ships with macOS. Set HOST_CHECK_FORCE=1 to run it on
# another OS (the tests do this with stubbed commands).

set -u
ONLY_GAPS=0
[ "${1:-}" = "--gaps" ] && ONLY_GAPS=1
GAPS=0

say() {  # status id message
  [ "$1" = "GAP" ] && GAPS=$((GAPS + 1))
  if [ $ONLY_GAPS -eq 0 ] || [ "$1" != "PASS" ]; then
    printf '%-6s %-22s %s\n' "$1" "$2" "$3"
  fi
}

if [ "$(uname -s)" != "Darwin" ] && [ "${HOST_CHECK_FORCE:-0}" != "1" ]; then
  echo "This check is for macOS." >&2
  exit 2
fi

UID_NUM=$(id -u)
PMSET_LIVE=$(pmset -g 2>/dev/null)
IS_LAPTOP=0
pmset -g batt 2>/dev/null | grep -q InternalBattery && IS_LAPTOP=1

# --- session -------------------------------------------------------------------------
if id -Gn | tr ' ' '\n' | grep -qx admin; then
  say MANUAL session.user "running as an admin user; fine on an interim host, use a standard user on a dedicated one"
else
  say PASS session.user "standard user $(id -un)"
fi

if pgrep -xq Claude 2>/dev/null; then
  say PASS session.desktop-app "Claude desktop app is running"
else
  say MANUAL session.desktop-app "Claude desktop app not running; needed only if you reach this Mac through it (add it to Login Items)"
fi

# --- security --------------------------------------------------------------------------
FV=$(fdesetup status 2>/dev/null)
case "$FV" in
  *"FileVault is On"*) say PASS security.filevault "FileVault on; make sure the restart plan says who unlocks it" ;;
  *"FileVault is Off"*) say GAP security.filevault "FileVault off; anyone who takes this Mac has the data (System Settings, Privacy & Security, FileVault)" ;;
  *) say MANUAL security.filevault "could not read FileVault status" ;;
esac

# --- power -------------------------------------------------------------------------------
if pmset -g ps 2>/dev/null | grep -q "AC Power"; then
  say PASS power.source "on mains power"
else
  say GAP power.source "running on battery; plug it in"
fi

SLEEP_VAL=$(printf '%s\n' "$PMSET_LIVE" | awk '$1=="sleep" {print $2; exit}')
if printf '%s\n' "$PMSET_LIVE" | grep -Eq 'SleepDisabled[[:space:]]+1'; then
  say PASS power.sleep "system sleep disabled"
elif [ "${SLEEP_VAL:-x}" = "0" ]; then
  say PASS power.sleep "system sleep 0 on the current power source"
else
  say GAP power.sleep "system sleep is '${SLEEP_VAL:-unknown}'; run: sudo pmset -c sleep 0 (laptop: sudo pmset disablesleep 1)"
fi

if printf '%s\n' "$PMSET_LIVE" | grep -Eq 'lowpowermode[[:space:]]+1'; then
  say GAP power.lowpower "Low Power Mode is on; it throttles every job. Run: sudo pmset -c lowpowermode 0"
else
  say PASS power.lowpower "Low Power Mode off"
fi

if [ $IS_LAPTOP -eq 1 ]; then
  say MANUAL power.charge-limit "laptop: confirm a charge limit around 80% (System Settings, Battery, (i) next to Charging)"
  say MANUAL power.lid "laptop: keep the lid open on a hard surface"
else
  if printf '%s\n' "$PMSET_LIVE" | grep -Eq 'autorestart[[:space:]]+1'; then
    say PASS power.autorestart "starts again after a power cut"
  else
    say GAP power.autorestart "will not start after a power cut; run: sudo pmset -a autorestart 1"
  fi
fi

# --- updates -------------------------------------------------------------------------------
SU=/Library/Preferences/com.apple.SoftwareUpdate
AUTO=$(defaults read "$SU" AutomaticallyInstallMacOSUpdates 2>/dev/null)
if [ "$AUTO" = "0" ]; then
  say PASS updates.auto-install "automatic macOS installs off"
else
  say GAP updates.auto-install "automatic macOS installs may restart this Mac overnight; turn off in System Settings, General, Software Update"
fi
CRIT=$(defaults read "$SU" CriticalUpdateInstall 2>/dev/null)
if [ "$CRIT" = "1" ]; then
  say PASS updates.security "security responses install automatically"
else
  say GAP updates.security "security responses not set to install; turn on in Software Update, Automatic Updates"
fi

# --- remote --------------------------------------------------------------------------------
if nc -z -w 2 127.0.0.1 22 >/dev/null 2>&1; then
  say PASS remote.ssh "Remote Login answering on port 22 locally"
else
  say MANUAL remote.ssh "Remote Login not answering; needed only for SSH access (System Settings, General, Sharing)"
fi

FW=${SOCKETFILTERFW:-/usr/libexec/ApplicationFirewall/socketfilterfw}
if "$FW" --getglobalstate 2>/dev/null | grep -qi "enabled"; then
  say PASS remote.firewall "firewall on"
else
  say GAP remote.firewall "firewall off; turn on in System Settings, Network, Firewall"
fi

if ifconfig 2>/dev/null | awk '/^utun/ {u=1} /^[a-z]/ && !/^utun/ {u=0} u && /inet 100\./ {f=1} END {exit !f}'; then
  say PASS remote.tunnel "a private device network is up (utun with a 100.x address)"
else
  say MANUAL remote.tunnel "no private device network seen; fine if you reach this Mac only through the Claude app"
fi

# --- claude -----------------------------------------------------------------------------------
CLAUDE_BIN=$(command -v claude 2>/dev/null)
[ -z "$CLAUDE_BIN" ] && [ -x "$HOME/.local/bin/claude" ] && CLAUDE_BIN="$HOME/.local/bin/claude"
if [ -n "$CLAUDE_BIN" ]; then
  say PASS claude.cli "claude at $CLAUDE_BIN"
  if "$CLAUDE_BIN" auth status >/dev/null 2>&1; then
    say PASS claude.auth "claude auth status reports signed in"
  else
    say GAP claude.auth "claude is not signed in for this user; run claude and sign in, or provide CLAUDE_CODE_OAUTH_TOKEN to jobs"
  fi
else
  say GAP claude.cli "claude not found"
fi
CLAUDE_DIR=$(dirname "${CLAUDE_BIN:-$HOME/.local/bin/claude}")

# --- jobs --------------------------------------------------------------------------------------
AGENT_DIR="$HOME/Library/LaunchAgents"
FOUND=0
for plist in "$AGENT_DIR"/*.plist; do
  [ -f "$plist" ] || continue
  label=$(plutil -extract Label raw -o - "$plist" 2>/dev/null)
  [ -z "$label" ] && continue
  case "$label" in com.apple.*|com.google.*|com.microsoft.*) continue ;; esac
  FOUND=$((FOUND + 1))
  info=$(launchctl print "gui/$UID_NUM/$label" 2>/dev/null)
  if [ -z "$info" ]; then
    say GAP jobs.agents "$label is not loaded; run: launchctl bootstrap gui/$UID_NUM $plist"
    continue
  fi
  last=$(printf '%s\n' "$info" | awk -F'= ' '/last exit code/ {print $2; exit}')
  case "${last:-0}" in
    0|"(never exited)") say PASS jobs.agents "$label loaded, last exit ${last:-none}" ;;
    *) say GAP jobs.failing "$label last exit code $last; read its log" ;;
  esac
  envpath=$(plutil -extract EnvironmentVariables.PATH raw -o - "$plist" 2>/dev/null)
  prog=$(plutil -extract ProgramArguments.0 raw -o - "$plist" 2>/dev/null)
  if printf '%s' "$envpath" | tr ':' '\n' | grep -qx "$CLAUDE_DIR"; then
    say PASS jobs.path "$label PATH includes $CLAUDE_DIR"
  elif [ -f "$prog" ] && grep -Eq 'PATH=|^[[:space:]]*(source|\.)[[:space:]]' "$prog"; then
    say PASS jobs.path "$label starts through a script that sets or sources PATH"
  else
    say GAP jobs.path "$label runs with launchd's bare PATH and may not find claude; set PATH in the plist or start it through a wrapper"
  fi
done
[ $FOUND -eq 0 ] && say MANUAL jobs.agents "no LaunchAgents of your own found in $AGENT_DIR"

if crontab -l 2>/dev/null | grep -Eq '^[^#[:space:]]'; then
  say MANUAL jobs.cron "cron entries present; cron skips runs missed during sleep, consider LaunchAgents"
fi

# --- host ----------------------------------------------------------------------------------------
PRESSURE=$(sysctl -n kern.memorystatus_vm_pressure_level 2>/dev/null)
case "$PRESSURE" in
  1) say PASS host.memory "memory pressure normal" ;;
  2) say MANUAL host.memory "memory pressure warning; watch swap over a few days" ;;
  4) say GAP host.memory "memory pressure critical" ;;
  *) say MANUAL host.memory "could not read memory pressure" ;;
esac

FREE=$(df -kP /System/Volumes/Data 2>/dev/null | awk 'NR==2 {gsub("%","",$5); print 100-$5}')
if [ -n "$FREE" ] && [ "$FREE" -ge 15 ]; then
  say PASS host.disk "${FREE}% disk free"
elif [ -n "$FREE" ]; then
  say GAP host.disk "only ${FREE}% disk free; below 15% macOS and git fail in odd ways"
else
  say MANUAL host.disk "could not read free disk"
fi

# --- backup and monitoring ---------------------------------------------------------------------
if tmutil destinationinfo 2>/dev/null | grep -q "^Name"; then
  say PASS backup.timemachine "a Time Machine destination is configured"
else
  say GAP backup.timemachine "no Time Machine destination"
fi
say MANUAL monitor.deadman "confirm an off-box dead-man check pings every 5 minutes and alerts you"

echo
if [ $GAPS -eq 0 ]; then echo "No gaps."; else echo "$GAPS gap(s)."; fi
[ $GAPS -eq 0 ]
