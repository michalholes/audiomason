# Configuration

AudioMason reads configuration from configuration.yaml.

## Recommended setup

Use a dedicated data directory and keep paths relative:

    export AUDIOMASON_DATA_ROOT="$HOME/audiomason_data"

All relative paths resolve relative to this directory.

## Minimal configuration

```yaml
paths:
  inbox: abooksinbox
  stage: _am_stage
  output: abooks_ready
  archive: abooks
  cache: am_cache
```

Copy configuration.minimal.yaml to configuration.yaml to start.

## Full configuration

See configuration.example.yaml for:
- all supported keys
- accepted values
- commented examples

## Notes

- pipeline_steps overrides internal defaults
- split_chapters controls M4A chapter splitting
- publish is a default only (CLI may override)
- ffmpeg options control encoding behavior
