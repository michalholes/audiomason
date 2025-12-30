from pathlib import Path
from audiomason.verify import verify_library

def test_verify_library_smoke(tmp_path, capsys):
    # Empty library should not crash
    verify_library(tmp_path)
    out = capsys.readouterr().out
    assert "done" in out.lower()
