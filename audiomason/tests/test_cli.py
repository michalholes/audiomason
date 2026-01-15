import subprocess
import sys

def test_cli_runs():
    """Ensure that the Audiomason CLI runs without error."""
    result = subprocess.run(
        [sys.executable, "-m", "audiomason.cli.main"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"CLI exited with code {result.returncode}"
    assert "Audiomason v2 pipeline executed" in result.stdout
