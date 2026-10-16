# Power and sleep

`pmset` keeps **separate settings for mains and battery**. Most "it never sleeps" setups are
only true on mains, and the first loose charger proves it. Read both:

```bash
pmset -g custom      # an "AC Power:" block and a "Battery Power:" block
pmset -g             # live values, including SleepDisabled
pmset -g ps          # which source it is drawing from now
```

## Settings

All of these need `sudo`, so a person runs them.

| Setting | Command | Laptop | Desktop | Why |
| --- | --- | --- | --- | --- |
| No system sleep at all | `sudo pmset disablesleep 1` | yes | optional | covers mains and battery in one switch |
| No system sleep on mains | `sudo pmset -c sleep 0` | covered above | yes | a sleeping host runs nothing |
| Low Power Mode off on mains | `sudo pmset -c lowpowermode 0` | yes | yes | on mains it only throttles every job |
| Start again after a power cut | `sudo pmset -a autorestart 1` | not possible | yes | a laptop cannot power itself on |
| Display sleep | leave it on | - | - | the screen sleeping does not stop jobs |

`-c` is mains (charger), `-b` battery, `-a` both. Check with `pmset -g custom` afterwards.

**Low Power Mode on mains is the quiet one.** Easy to leave on after travelling, it shows no
error, and it can double how long every job takes.

## Laptop only

- **Charge limit.** A laptop on mains all day should stop charging around 80%. On recent macOS
  it is in System Settings, Battery, then the (i) next to Charging (see
  [changes-ledger.md](changes-ledger.md) for the version). It cannot be read reliably from the
  command line, so the check asks a person to confirm it.
- **Keep it plugged in.** A host on battery has hours left, not days.
- **Lid open, on a hard surface.** With the lid closed and no external display the Mac sleeps
  regardless of `pmset`, and a soft surface traps heat on a fanless model.

## Desktop only

A small UPS for the Mac and the router rides out short cuts and lets the Mac shut down cleanly
on a long one (connect it by USB; its settings then appear under Battery or Energy). With
`autorestart 1` the Mac comes back when power returns. If FileVault is on, it then waits at the
unlock screen: see [login-session-and-restarts.md](login-session-and-restarts.md).
