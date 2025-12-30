# AudioMason (dev skeleton)

This is a minimal, working skeleton for the AudioMason CLI.

## Commands

- `audiomason inspect PATH`
- `audiomason process PATH [--yes]`

For containerized runs, use `make build`, `make inspect P=...`, `make process P=...`.

Requires `/etc/audiomason/config.yaml` on the runtime host (or set `AUDIOMASON_CONFIG`).
