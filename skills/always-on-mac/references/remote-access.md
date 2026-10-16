# Reaching the host from anywhere

Two layers: an everyday way in, and a fallback for when the everyday way is stuck. Pick one of
each, keep it simple, and keep the keys with you.

| Layer | What it gives | Cost |
| --- | --- | --- |
| 1. The Claude desktop app on the host, used from another device | everyday work from anywhere: files and shell | nothing extra |
| 2. A keep-alive for the app | it comes back by itself after a crash or quit | nothing |
| 3. A private device network | SSH and screen sharing when the app is down | free tiers exist |
| 4. A person at the Mac | the FileVault unlock after a restart, if SSH unlock is not set up | - |

## Layer 2: keep the bridge up

Add the Claude app to Login Items, and a small LaunchAgent that checks every few minutes and
reopens it if it has gone. Run it outside any job lock: a five-minute check must not queue
behind a forty-minute job.

```bash
pgrep -xq Claude || open -g -a Claude
```

## Layer 3: a private device network

A mesh VPN links your own devices into one encrypted network, device to device. No port is
opened on the router and nothing of yours sits on the public internet. Options, as checked on
the dates in [changes-ledger.md](changes-ledger.md):

| Option | Runs on | When to choose it |
| --- | --- | --- |
| Tailscale | a client on each device | the common default; free Personal plan for personal (non-commercial) use, decided by the sign-in domain: a Gmail, Apple or personal GitHub sign-in gets it, a custom work domain starts a business trial |
| NordVPN Meshnet | the NordVPN app on each device | free and needs no VPN subscription; good if you already use NordVPN |
| Cloudflare Tunnel with Access | `cloudflared` on the host | you already run DNS on Cloudflare and want browser-gated SSH |
| Headscale | your own public server | you want the control plane entirely yours |
| WireGuard to your router | the router | your router supports it and you can keep a DNS name pointed at home |

Run **one** private network, not two: two meshes on one Mac compete for the same address range
and make faults hard to read.

Rules for the host:

- **Do not connect the host itself to a VPN exit server.** The mesh works without it.
  Routing all traffic through an exit changes the address every job appears from, which trips
  sign-in challenges and IP allowlists.
- Remove remote-access permission for any linked device that should not reach the host.
- When you move to a new Mac, build it fresh and sign in to the mesh again; a restored copy can
  clash with the original's device identity ([choosing-and-migrating.md](choosing-and-migrating.md)).

## Remote Login and the firewall

Whatever the network, the host side is macOS Remote Login (System Settings, General, Sharing):
only your user, key authentication, and never port 22 open to the internet. Turn the firewall
on (System Settings, Network, Firewall); Remote Login stays reachable through it.

From your phone or laptop on the mesh: `ssh you@<host's mesh name>`. Screen Sharing works the
same way.
