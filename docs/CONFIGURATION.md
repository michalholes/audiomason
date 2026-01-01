
# Configuration

AudioMason loads configuration from `configuration.yaml` in the app root by default.

## Recommended setup

Use a dedicated data directory and keep config paths relative:

- `AUDIOMASON_ROOT`: points to the app/repo root (contains `pyproject.toml`)
- `AUDIOMASON_DATA_ROOT`: points to your data root (recommended)

Example:

    export AUDIOMASON_DATA_ROOT="$HOME/audiomason_data"

Then:

- `paths.inbox: abooksinbox` resolves to `$AUDIOMASON_DATA_ROOT/abooksinbox`
- same for stage/output/archive/cache

## Keys

- `paths.*`: main roots (inbox, stage, output, archive, cache)
- `pipeline_steps`: optional pipeline order override
- `split_chapters`: split chapterized M4A into multiple MP3 tracks when possible
- `ffmpeg.*`: ffmpeg loglevel and encoding options

See `configuration.example.yaml` for a fully commented template.
