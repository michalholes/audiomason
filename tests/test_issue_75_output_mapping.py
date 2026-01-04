from pathlib import Path
import audiomason.import_flow as imp


def test_issue_75_output_dir_single_source():
    dest = Path("/tmp/out")
    assert imp._output_dir(dest, None, Path(".")) == dest
    assert imp._output_dir(dest, None, Path("seria/kniha1")) == dest / "seria/kniha1"


def test_issue_75_output_dir_all_sources_prefix():
    dest = Path("/tmp/out")
    assert imp._output_dir(dest, "Jano", Path(".")) == dest / "Jano"
    assert imp._output_dir(dest, "Jano", Path("seria/kniha1")) == dest / "Jano" / "seria/kniha1"
