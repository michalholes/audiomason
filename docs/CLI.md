# CLI reference

This document is the CLI contract for AudioMason.

## Summary

AudioMason provides these subcommands:

- import: import audiobooks from inbox
- verify: verify audiobook library
- inspect: read-only source inspection
- cache: cache maintenance

Configuration keys live in configuration.yaml (see docs/CONFIGURATION.md).
Runtime behavior is controlled by CLI flags and subcommand options.

## Config vs CLI

- Configuration defines defaults and filesystem roots.
- CLI flags override defaults for the current run.
- Processing is designed to be deterministic and resumable.

## Full `--help` output

```text
usage: audiomason [-h] [--yes] [--dry-run] [--quiet] [--verbose] [--debug]
                  [--json] [--config CONFIG] [--verify]
                  [--verify-root VERIFY_ROOT] [--lookup | --no-lookup]
                  [--publish {yes,no,ask}] [--wipe-id3 | --no-wipe-id3]
                  [--loudnorm] [--q-a Q_A] [--split-chapters]
                  [--no-split-chapters] [--cpu-cores CPU_CORES]
                  [--ff-loglevel {info,warning,error}] [--version]
                  {import,verify,inspect,cache} ...

AudioMason – audiobook import & maintenance tool

positional arguments:
  {import,verify,inspect,cache}
    import              import audiobooks from inbox
    verify              verify audiobook library
    inspect             read-only source inspection
    cache               cache maintenance

options:
  -h, --help            show this help message and exit
  --yes                 non-interactive
  --dry-run             do not modify anything
  --quiet               less output
  --verbose             more output (overrides --quiet)
  --debug               prefix every out() line with [TRACE]
  --json                print machine-readable JSON report at end
  --config CONFIG       explicit configuration.yaml path
  --verify              verify library after import
  --verify-root VERIFY_ROOT
                        root for --verify
  --lookup              enable OpenLibrary validation
  --no-lookup           disable OpenLibrary validation
  --publish {yes,no,ask}
  --wipe-id3            full wipe ID3 tags before writing new tags
  --no-wipe-id3         do not wipe ID3 tags (default)
  --loudnorm
  --q-a Q_A             lame VBR quality (2=high)
  --split-chapters
  --no-split-chapters
  --cpu-cores CPU_CORES
                        override CPU core count for perf tuning
  --ff-loglevel {info,warning,error}
  --version             show version and exit
```
