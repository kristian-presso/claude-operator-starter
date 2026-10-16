# Choosing a host, and moving to a new one

## Laptop or desktop

A **desktop Mac (a Mac mini or Mac Studio)** is the right long-term host: no battery to age, it
can start itself after a power cut (`pmset autorestart`), it takes wired Ethernet, and it sits
happily on a UPS.

A **laptop** works as an interim host and is a good rehearsal, with three costs: the battery
ages if it sits at 100% (set the charge limit), it cannot power itself back on after a cut, and
a fanless model throttles under sustained load, so job times on it are a worst case.

## How much memory

Memory cannot be upgraded later, so size it from evidence:

- **Claude does the thinking and any local models are small:** 32GB is plenty.
- **A large local model (30B-class) is central to the work:** 64GB or more.

Log memory pressure and swap for a few weeks first (the heartbeat in
[monitoring.md](monitoring.md) does this). If swap is regularly full under normal load, go up a
tier. Disk: 1TB leaves room for repos, worktrees, caches and models; under 15% free, macOS and
git start failing in odd ways.

## Use the laptop you have first

Running the setup on a laptop you already own for a few weeks answers the hardware questions
with real numbers and makes the move to a dedicated machine an afternoon's work. Write down
every manual fix: each one is a step the next machine's setup must include.

## Moving to a new host

The goal is an afternoon. It is one if the old host's setup lives in repos and a written
playbook, not in your memory.

**Do not use Migration Assistant or a Time Machine restore for the host role.** It copies the
old machine's accumulated state, including the faults you are moving to escape, and identities
that must stay unique (a mesh VPN client's device identity, for one).

Order:

1. Build the new host fresh from [setup-playbook.md](setup-playbook.md) through the tools stage.
   The old one keeps running.
2. Clone the repos; sign in Claude and the secrets manager.
3. **Stop the old host's jobs** (`launchctl bootout` each) and let its last sync push.
4. Pull on the new host, generate and load its LaunchAgents, run the register check.
5. Point the dead-man checks at the new host (same URLs; the old one simply stops pinging).
6. Copy what git does not hold, from the off-site snapshot.
7. Run the health check. Watch one full day of runs before wiping the old machine.

Two hosts running the same jobs at once will both commit and push, and both believe they own the
schedule. Step 3 before step 4, always.
