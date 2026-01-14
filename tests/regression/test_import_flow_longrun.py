"""Regression Test: Long-running import_flow stability"""
import hashlib, json, pytest
from pathlib import Path
from audiomason import import_flow

@pytest.mark.longrun
def test_import_flow_determinism(tmp_path: Path):
    results = []
    for i in range(10):
        output_dir = tmp_path / f"run_{i}"
        output_dir.mkdir()
        import_flow.run_import(source="tests/fixtures/basic_source", output=output_dir, dry_run=True, yes=True)
        report_file = output_dir / "report.json"
        with open(report_file, "rb") as f:
            results.append(hashlib.sha256(f.read()).hexdigest())
    assert len(set(results)) == 1, "Non-deterministic import results detected"
